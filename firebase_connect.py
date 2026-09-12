import json
import requests
import uuid
from datetime import datetime
from typing import Any, Dict, List

firebase_config = {
    "apiKey": "AIzaSyCAxSzibIToke3_K2KpdCDSelq9gYRWE6Y",
    "authDomain": "hgfygy-2aea2.firebaseapp.com",
    "projectId": "hgfygy-2aea2",
    "storageBucket": "hgfygy-2aea2.firebasestorage.app",
    "messagingSenderId": "856388248157",
    "appId": "1:856388248157:web:dbd2a2976642b452d823b4",
    "measurementId": "G-61YCMZR0K1",
}

PROJECT_ID = firebase_config["projectId"]
API_KEY = firebase_config["apiKey"]
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
MESSAGES_COLLECTION = "messages"
USERS_COLLECTION = "users"
PRIVATE_MESSAGES_COLLECTION = "private_messages"
PUBLIC_MESSAGES_COLLECTION = "public_messages"
GROUPS_COLLECTION = "groups"


def firestore_value(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if value is None:
        return {"nullValue": None}
    if isinstance(value, dict):
        return {"mapValue": {"fields": to_firestore_fields(value)}}
    if isinstance(value, list):
        return {"arrayValue": {"values": [firestore_value(item) for item in value]}}
    raise TypeError(f"Unsupported Firestore field type: {type(value)}")


def to_firestore_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: firestore_value(value) for key, value in data.items()}


def from_firestore_value(value: Dict[str, Any]) -> Any:
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return value["doubleValue"]
    if "booleanValue" in value:
        return value["booleanValue"]
    if "mapValue" in value:
        return {k: from_firestore_value(v) for k, v in value["mapValue"]["fields"].items()}
    if "arrayValue" in value:
        return [from_firestore_value(v) for v in value["arrayValue"].get("values", [])]
    if "nullValue" in value:
        return None
    return None


def parse_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    fields = doc.get("fields", {})
    return {key: from_firestore_value(value) for key, value in fields.items()}


def create_or_update_document(collection: str, document_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a Firestore document with the given fields."""
    url = f"{BASE_URL}/{collection}/{document_id}"
    payload = {"fields": to_firestore_fields(fields)}
    response = requests.patch(url, params={"key": API_KEY}, json=payload)
    response.raise_for_status()
    return response.json()


def list_documents(collection: str) -> Dict[str, Any]:
    """List documents in a Firestore collection."""
    url = f"{BASE_URL}/{collection}"
    response = requests.get(url, params={"key": API_KEY})
    response.raise_for_status()
    return response.json()


def send_message(text: str, sender: str) -> Dict[str, Any]:
    """Send a chat message to Firestore."""
    document_id = uuid.uuid4().hex
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return create_or_update_document(
        MESSAGES_COLLECTION,
        document_id,
        {
            "sender": sender,
            "text": text,
            "createdAt": created_at,
        },
    )


def list_messages(limit: int = 100) -> List[Dict[str, Any]]:
    """List recent chat messages from Firestore."""
    payload = list_documents(MESSAGES_COLLECTION)
    documents = payload.get("documents", [])
    messages = [parse_document(doc) for doc in documents]
    sorted_messages = sorted(messages, key=lambda msg: msg.get("createdAt", ""))
    return sorted_messages[:limit]


def register_user(username: str, password: str, ip_address: str = "") -> Dict[str, Any]:
    """Register a new user."""
    import hashlib
    
    # Check if user already exists
    try:
        existing_user = get_user(username)
        if existing_user:
            raise ValueError(f"user name'{username}' Already exists")
    except:
        pass  # User doesn't exist, proceed
    
    # Hash password (simple SHA256 - NOT for production)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    return create_or_update_document(
        USERS_COLLECTION,
        username,  # Use username as document ID
        {
            "username": username,
            "passwordHash": password_hash,
            "createdAt": created_at,
            "status": "active",
            "registrationIp": ip_address,
        },
    )


def update_user_password(username: str, password: str) -> Dict[str, Any]:
    """Update a user's password while preserving the other account fields."""
    import hashlib

    user = get_user(username)
    if not user:
        raise ValueError("User does not exist")

    user["passwordHash"] = hashlib.sha256(password.encode()).hexdigest()
    user.pop("email", None)
    return create_or_update_document(USERS_COLLECTION, username, user)


def get_user(username: str) -> Dict[str, Any] | None:
    """Get user by username."""
    url = f"{BASE_URL}/{USERS_COLLECTION}/{username}"
    try:
        response = requests.get(url, params={"key": API_KEY})
        response.raise_for_status()
        doc = response.json()
        return parse_document(doc) if doc.get("fields") else None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def login_user(username: str, password: str) -> Dict[str, Any] | None:
    """Authenticate user by username and password."""
    import hashlib
    
    user = get_user(username)
    if not user:
        return None
    
    # Verify password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user.get("passwordHash") != password_hash:
        return None
    
    return user


def list_users() -> List[Dict[str, Any]]:
    """List all users."""
    payload = list_documents(USERS_COLLECTION)
    documents = payload.get("documents", [])
    users = [parse_document(doc) for doc in documents]
    return sorted(users, key=lambda u: u.get("createdAt", ""))


def send_private_message(text: str, sender: str, recipient: str) -> Dict[str, Any]:
    """Send a private message between two users."""
    # Create a conversation ID (sorted usernames for consistent ordering)
    users = sorted([sender, recipient])
    conversation_id = f"{users[0]}_{users[1]}"
    
    document_id = uuid.uuid4().hex
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    return create_or_update_document(
        f"{PRIVATE_MESSAGES_COLLECTION}/{conversation_id}/messages",
        document_id,
        {
            "sender": sender,
            "recipient": recipient,
            "text": text,
            "createdAt": created_at,
        },
    )


def get_private_conversation(user1: str, user2: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get private conversation between two users."""
    users = sorted([user1, user2])
    conversation_id = f"{users[0]}_{users[1]}"
    
    url = f"{BASE_URL}/{PRIVATE_MESSAGES_COLLECTION}/{conversation_id}/messages"
    try:
        response = requests.get(url, params={"key": API_KEY})
        response.raise_for_status()
        payload = response.json()
        documents = payload.get("documents", [])
        messages = [parse_document(doc) for doc in documents]
        sorted_messages = sorted(messages, key=lambda msg: msg.get("createdAt", ""))
        return sorted_messages[-limit:]  # Return last N messages
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []
        raise


def send_public_message(text: str, sender: str) -> Dict[str, Any]:
    """Send a message to the public group chat."""
    document_id = uuid.uuid4().hex
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    return create_or_update_document(
        PUBLIC_MESSAGES_COLLECTION,
        document_id,
        {
            "sender": sender,
            "text": text,
            "createdAt": created_at,
        },
    )


def get_public_messages(limit: int = 100) -> List[Dict[str, Any]]:
    """Get public group chat messages."""
    payload = list_documents(PUBLIC_MESSAGES_COLLECTION)
    documents = payload.get("documents", [])
    messages = [parse_document(doc) for doc in documents]
    sorted_messages = sorted(messages, key=lambda msg: msg.get("createdAt", ""))
    return sorted_messages[-limit:]  # Return last N messages


def create_group(group_name: str, creator: str, members: List[str]) -> Dict[str, Any]:
    """Create a new group chat."""
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    # Ensure creator is in members
    if creator not in members:
        members.append(creator)
    
    return create_or_update_document(
        GROUPS_COLLECTION,
        group_name,
        {
            "name": group_name,
            "creator": creator,
            "members": members,
            "createdAt": created_at,
        },
    )


def get_group(group_name: str) -> Dict[str, Any] | None:
    """Get group information."""
    url = f"{BASE_URL}/{GROUPS_COLLECTION}/{group_name}"
    try:
        response = requests.get(url, params={"key": API_KEY})
        response.raise_for_status()
        doc = response.json()
        return parse_document(doc) if doc.get("fields") else None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def join_group(group_name: str, username: str) -> bool:
    """Add a user to a group."""
    try:
        group = get_group(group_name)
        if not group:
            return False
        
        members = group.get("members", [])
        if username not in members:
            members.append(username)
            create_or_update_document(
                GROUPS_COLLECTION,
                group_name,
                {
                    "name": group.get("name"),
                    "creator": group.get("creator"),
                    "members": members,
                    "createdAt": group.get("createdAt"),
                },
            )
        return True
    except Exception:
        return False


def leave_group(group_name: str, username: str) -> bool:
    """Remove a user from a group."""
    try:
        group = get_group(group_name)
        if not group:
            return False
        
        members = group.get("members", [])
        if username in members:
            members.remove(username)
            create_or_update_document(
                GROUPS_COLLECTION,
                group_name,
                {
                    "name": group.get("name"),
                    "creator": group.get("creator"),
                    "members": members,
                    "createdAt": group.get("createdAt"),
                },
            )
        return True
    except Exception:
        return False


def list_groups() -> List[Dict[str, Any]]:
    """List all groups."""
    payload = list_documents(GROUPS_COLLECTION)
    documents = payload.get("documents", [])
    groups = [parse_document(doc) for doc in documents]
    return sorted(groups, key=lambda g: g.get("createdAt", ""))


def send_group_message(text: str, sender: str, group_name: str) -> Dict[str, Any]:
    """Send a message to a group."""
    document_id = uuid.uuid4().hex
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    return create_or_update_document(
        f"{GROUPS_COLLECTION}/{group_name}/messages",
        document_id,
        {
            "sender": sender,
            "text": text,
            "createdAt": created_at,
        },
    )


def get_group_messages(group_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get messages from a group."""
    url = f"{BASE_URL}/{GROUPS_COLLECTION}/{group_name}/messages"
    try:
        response = requests.get(url, params={"key": API_KEY})
        response.raise_for_status()
        payload = response.json()
        documents = payload.get("documents", [])
        messages = [parse_document(doc) for doc in documents]
        sorted_messages = sorted(messages, key=lambda msg: msg.get("createdAt", ""))
        return sorted_messages[-limit:]  # Return last N messages
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []
        raise


def get_user_groups(username: str) -> List[Dict[str, Any]]:
    """Get all groups a user is a member of."""
    try:
        all_groups = list_groups()
        user_groups = [g for g in all_groups if username in g.get("members", [])]
        return user_groups
    except Exception:
        return []


if __name__ == "__main__":
    print("Testing Firestore chat functions")
    sent = send_message(text="Welcome", sender="order")
    print(json.dumps(sent, ensure_ascii=False, indent=2))
    print("\n Current messages:")
    for msg in list_messages():
        print(msg)
