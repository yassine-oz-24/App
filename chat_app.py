import json
import os
import socket
from getpass import getpass
from pathlib import Path

from firebase_connect import (
    register_user,
    login_user,
    get_user,
    update_user_password,
    list_users,
    get_private_conversation,
    send_private_message,
    create_group,
    get_group,
    join_group,
    leave_group,
    list_groups,
    send_group_message,
    get_group_messages,
    get_user_groups,
)


class ChatApp:
    """Command-based chat application."""
    
    SESSION_FILE = Path.home() / ".pychat_session"
    
    def __init__(self) -> None:
        self.user = None
        self.username = None
        self.running = True
        self._load_session()
        self._show_banner()
        self._show_home_screen()
        self._command_loop()
    
    def _show_banner(self) -> None:
        """Show welcome banner."""
        print("\n+---------------------------------+")
        print("|          nsele - chat            |")
        print("+---------------------------------+\n")
    
    def _show_help(self) -> None:
        """Show the short command list."""
        print("\nQuick commands:")
        print("  u                  users")
        print("  g                  my groups")
        print("  m <name>           open a chat")
        print("  s <name>           send a private message")
        print("  home               show chats")
        print("  clear              clear terminal")
        print("  h                  help")
        print("  q                  exit")
        print("\nLogin: fox lg   Register: fox rg   Password: pw")
        print("Logout: logout")
        print("Old commands are still supported.\n")

    @staticmethod
    def _device_ip() -> str:
        """Get the device's local network address without displaying it."""
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            connection.connect(("8.8.8.8", 80))
            ip_address = connection.getsockname()[0]
            connection.close()
            return ip_address
        except OSError:
            return "unknown"

    
    def _save_session(self) -> None:
        """Save user session to local file."""
        if self.username:
            try:
                with open(self.SESSION_FILE, "w") as f:
                    json.dump({"username": self.username}, f)
            except Exception as e:
                print(f"  Warning: Failed to save session: {e}")
    
    def _load_session(self) -> None:
        """Load user session from local file."""
        if self.SESSION_FILE.exists():
            try:
                with open(self.SESSION_FILE, "r") as f:
                    data = json.load(f)
                    self.username = data.get("username")
                    # Try to get user info from Firebase
                    try:
                        self.user = get_user(self.username)
                    except:
                        self.username = None
            except Exception as e:
                print(f"  Warning: Failed to load session: {e}")

    def _show_home_screen(self) -> None:
        """Show the logged-in user and chats ordered by recent activity."""
        if not self.username:
            return

        try:
            users = list_users()
            user_chats = []
            for user in users:
                other_username = user.get("username")
                if not other_username or other_username == self.username:
                    continue
                messages = get_private_conversation(self.username, other_username)
                user_chats.append({
                    "name": other_username,
                    "kind": "user",
                    "messages": messages,
                })

            group_chats = []
            for group in get_user_groups(self.username):
                group_name = group.get("name")
                if not group_name:
                    continue
                group_chats.append({
                    "name": group_name,
                    "kind": "group",
                    "messages": get_group_messages(group_name),
                })

            chats = user_chats + group_chats
            chats.sort(
                key=lambda chat: (
                    bool(chat["messages"]),
                    chat["messages"][-1].get("createdAt", "")
                    if chat["messages"] else "",
                ),
                reverse=True,
            )

            print(f" Account: {self.username}\n")
            print("Chats (type a username or group name to open it):")
            if not chats:
                print("  No other accounts or groups found")
            else:
                for chat in chats:
                    marker = "*" if chat["messages"] else " "
                    label = "group" if chat["kind"] == "group" else "user"
                    print(f"  {marker} {chat['name']} [{label}]"
                          f" ({len(chat['messages'])} message(s))")
            print()
        except Exception as e:
            print(f" Error loading chats: {str(e)[:80]}\n")

    @staticmethod
    def _clear_terminal() -> None:
        """Clear the terminal screen on desktop shells and Termux."""
        os.system("cls" if os.name == "nt" else "clear")

    def _open_chat(self, name: str) -> None:
        """Open a private chat or group by its name."""
        if not self.username:
            print(" You must be logged in first\n")
            return

        try:
            user = get_user(name)
            if user and name != self.username:
                messages = get_private_conversation(self.username, name)
                print(f"\nChat with {name}:\n")
                self._print_chat_messages(messages)
                self._chat_loop(name, is_group=False)
                return

            group = get_group(name)
            if group and self.username in group.get("members", []):
                messages = get_group_messages(name)
                print(f"\nGroup chat: {name}\n")
                self._print_chat_messages(messages)
                self._chat_loop(name, is_group=True)
                return

            print(f" Chat '{name}' was not found or you are not a member\n")
        except Exception as e:
            print(f" Error opening chat: {str(e)[:80]}\n")

    @staticmethod
    def _print_chat_messages(messages) -> None:
        """Print chat messages in a compact format."""
        if not messages:
            print("  No messages yet")
        for message in messages:
            sender = message.get("sender", "Unknown")
            print(f"  {sender}: {message.get('text', '')}")
        print("\nType /s to leave the chat.\n")

    def _chat_loop(self, name: str, is_group: bool) -> None:
        """Keep the user in a chat until /s is entered."""
        while self.running:
            message = input(f"{self.username} >>> ").strip()
            if message.lower() == "/s":
                print()
                self._show_home_screen()
                return
            if not message:
                continue

            try:
                if is_group:
                    send_group_message(message, self.username, name)
                else:
                    send_private_message(message, self.username, name)
                print("  Sent")
            except Exception as e:
                print(f" Error sending message: {str(e)[:80]}\n")
    
    def _clear_session(self) -> None:
        """Clear saved session."""
        try:
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
        except Exception as e:
            print(f"  Warning: Failed to delete session: {e}")
    
    def _login(self, username: str, password: str) -> bool:
        """Handle login."""
        if self.username:
            print(f" You are already logged in as:{self.username}\n")
            return False
        
        try:
            user = login_user(username, password)
            if user:
                self.user = user
                self.username = username
                self._save_session()
                print(f"\n Successfully logged in")
                print(f"   User: {username}")
                print()
                return True
            else:
                print(" Error: Invalid username or password\n")
                return False
        except Exception as e:
            print(f" Error logging in: {str(e)[:80]}\n")
            return False
    
    def _register(self, username: str, password: str, password_confirm: str) -> bool:
        """Handle registration."""
        if self.username:
            print(f" You are already registered as: {self.username}\n")
            return False
        
        # Validate inputs
        if not all([username, password, password_confirm]):
            print(" Username and password are required\n")
            return False
        
        if password != password_confirm:
            print(" Passwords do not match\n")
            return False
        
        if len(password) < 6:
            print(" Password must be at least 6 characters long\n")
            return False
        
        try:
            register_user(username, password, self._device_ip())
            print(f"\n Successfully created account")
            print(f"  User: {username}")
            
            # Auto-login
            self.user = get_user(username)
            self.username = username
            self._save_session()
            print(" Successfully logged in automatically\n")
            return True
        except Exception as e:
            error_msg = str(e)
            if "موجود" in error_msg or "exists" in error_msg.lower():
                print(f" اسم المستخدم '{username}' موجود بالفعل\n")
            else:
                print(f" Error registering: {error_msg[:80]}\n")
            return False

    def _change_password(self) -> None:
        """Change the current user's password."""
        if not self.username:
            print(" You must be logged in first\n")
            return

        current_password = getpass("Current password: ")
        if not login_user(self.username, current_password):
            print(" Incorrect current password\n")
            return

        new_password = getpass("New password: ")
        confirmation = getpass("Confirm new password: ")
        if len(new_password) < 6:
            print(" Password must be at least 6 characters long\n")
            return
        if new_password != confirmation:
            print(" Passwords do not match\n")
            return

        try:
            update_user_password(self.username, new_password)
            print(" Password changed successfully\n")
        except Exception as e:
            print(f" Error changing password: {str(e)[:80]}\n")
    
    def _show_messages_from_user(self, other_username: str) -> None:
        """Display private messages from a specific user."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        try:
            messages = get_private_conversation(self.username, other_username)
            
            if not messages:
                print(f" No messages from {other_username}\n")
                return
            
            # Filter messages from the other user
            user_messages = [m for m in messages if m.get("sender") == other_username]
            
            if not user_messages:
                print(f" No messages from {other_username}\n")
                return
            
            print(f"\nMessages from {other_username} ({len(user_messages)} message(s)):\n")
            for msg in user_messages:
                timestamp = msg.get("createdAt", "")
                text = msg.get("text", "")
                print(f"  [{timestamp}] {text}")
            print()
        except Exception as e:
            print(f" Error: {str(e)[:80]}\n")
    
    def _send_private_message(self, recipient: str) -> None:
        """Send a private message to a user."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        if recipient == self.username:
            print(" You cannot send a message to yourself\n")
            return
        
        # Check if user exists
        try:
            user = get_user(recipient)
            if not user:
                print(f" User '{recipient}' does not exist\n")
                return
        except:
            print(f" User '{recipient}' does not exist\n")
            return
        
        message_text = input("Message: ").strip()
        if not message_text:
            print(" Message cannot be empty\n")
            return
        
        try:
            send_private_message(message_text, self.username, recipient)
            print(f" Message sent to {recipient}\n")
        except Exception as e:
            print(f" Error sending message: {str(e)[:80]}\n")
    
    def _list_users(self) -> None:
        """Display all registered users."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        try:
            users = list_users()
            other_users = [u for u in users if u.get("username") != self.username]
            
            if not other_users:
                print(" No other users found  \n")
                return
            
            print(f"\n Users ({len(other_users)}):\n")
            for user in other_users:
                username = user.get("username", "Unknown    ")
                print(f"  • {username}")
                print()
        except Exception as e:
            print(f" Error: {str(e)[:80]}\n")
    
    def _create_group(self, group_name: str) -> None:
        """Create a new group."""
        if not self.username:
            print("  You must be logged in first\n")
            return
        
        # Check if group already exists
        try:
            existing_group = get_group(group_name)
            if existing_group:
                print(f" Group '{group_name}' already exists\n")
                return
        except:
            pass
        
        try:
            create_group(group_name, self.username, [self.username])
            print(f"\n Group '{group_name}' created successfully\n")
        except Exception as e:
            print(f" Error creating group: {str(e)[:80]}\n")
    
    def _join_group(self, group_name: str) -> None:
        """Join a group."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        try:
            group = get_group(group_name)
            if not group:
                print(f" Group '{group_name}' does not exist\n")
                return
            
            members = group.get("members", [])
            if self.username in members:
                print(f" You are already a member of the group '{group_name}'\n")
                return
            
            if join_group(group_name, self.username):
                print(f"\n Successfully joined the group '{group_name}'\n")
            else:
                print(f" Failed to join the group '{group_name}'\n")
        except Exception as e:
            print(f" Error: {str(e)[:80]}\n")
    
    def _leave_group(self, group_name: str) -> None:
        """Leave a group."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        try:
            if leave_group(group_name, self.username):
                print(f"\n Successfully left the group '{group_name}'\n")
            else:
                print(f" Failed to leave the group '{group_name}'\n")
        except Exception as e:
            print(f" Error: {str(e)[:80]}\n")

    
    def _list_user_groups(self) -> None:
        """List groups the user is a member of."""
        if not self.username:
            print(" You must be logged in first\n")
            return
        
        try:
            user_groups = get_user_groups(self.username)
            
            if not user_groups:
                print(" No groups found\n")
                return
            
            print(f"\n Groups ({len(user_groups)}):\n")
            for group in user_groups:
                name = group.get("name", "Unknown")
                creator = group.get("creator", "Unknown")
                members = group.get("members", [])
                print(f"  • {name}")
                print(f"    Creator: {creator}")
                print(f"    Members: {len(members)}")
                print()
        except Exception as e:
            print(f"Error: {str(e)[:80]}\n")
    
    def _send_group_message(self, group_name: str) -> None:
        """Send a message to a group."""
        if not self.username:
            print("You must be logged in first\n")
            return
        
        try:
            group = get_group(group_name)
            if not group:
                print(f"Group '{group_name}' does not exist\n")
                return
            
            members = group.get("members", [])
            if self.username not in members:
                print(f"You are not a member of the group '{group_name}'\n")
                return
            
            message_text = input("Message: ").strip()
            if not message_text:
                print("Message cannot be empty\n")
                return
            
            send_group_message(message_text, self.username, group_name)
            print(f" Message sent to {group_name}\n")
        except Exception as e:
            print(f"Error sending message: {str(e)[:80]}\n")

    def _show_group_messages(self, group_name: str) -> None:
        """Display messages from a group."""
        if not self.username:
            print("You must be logged in first\n")
            return
        
        try:
            group = get_group(group_name)
            if not group:
                print(f"Group '{group_name}' does not exist\n")
                return
            
            members = group.get("members", [])
            if self.username not in members:
                print(f"You are not a member of the group '{group_name}'\n")
                return
            
            messages = get_group_messages(group_name)
            
            if not messages:
                print(f"No messages found in the group '{group_name}'\n")
                return
            
            print(f"\nMessages in group '{group_name}':\n")
            for msg in messages:
                timestamp = msg.get("createdAt", "")
                sender = msg.get("sender", "Unknown")
                text = msg.get("text", "")
                print(f"  [{timestamp}] {sender}: {text}")
            print()
        except Exception as e:
            print(f"Error: {str(e)[:80]}\n")
    
    def _command_loop(self) -> None:
        """Main command loop."""
        while self.running:
            try:
                command = input("FOX$ >>> ").strip()
                
                if not command:
                    continue
                
                # Parse command
                parts = command.split()
                
                # Exit
                if command.lower() in ("q", "exit"):
                    self.running = False
                    break

                # Terminal navigation
                elif command.lower() == "clear":
                    self._clear_terminal()
                    self._show_banner()
                    if self.username:
                        self._show_home_screen()
                    else:
                        self._show_help()
                elif command.lower() in ("home", "refresh"):
                    self._show_home_screen()
                
                # Login: fox lg
                elif len(parts) >= 2 and parts[0] == "fox" and parts[1] == "lg":
                    username = input("Username: ").strip()
                    password = getpass("Password: ")
                    if self._login(username, password):
                        self._show_home_screen()
                
                # Register: fox rg
                elif len(parts) >= 2 and parts[0] == "fox" and parts[1] == "rg":
                    username = input("Username: ").strip()
                    password = getpass("Password: ")
                    password_confirm = getpass("Confirm password: ")
                    if self._register(username, password, password_confirm):
                        self._show_home_screen()

                # Change password
                elif command.lower() in ("pw", "password", "change-password"):
                    self._change_password()
                
                # Logout
                elif command.lower() == "logout":
                    if self.username:
                        print(f"\n Logged out from account {self.username}\n")
                        self.username = None
                        self.user = None
                        self._clear_session()
                        self._show_help()
                    else:
                        print("You are not logged in\n")
                
                # Show messages: show -msg -username
                elif len(parts) >= 3 and parts[0] == "show" and parts[1] == "-msg":
                    username = parts[2]
                    self._show_messages_from_user(username)
                
                # Send message: send -msg -username
                elif len(parts) >= 3 and parts[0] == "send" and parts[1] == "-msg":
                    username = parts[2]
                    self._send_private_message(username)
                
                # List users
                elif command.lower() == "list -users":
                    self._list_users()
                
                # Create group: create -group -groupname
                elif len(parts) >= 3 and parts[0] == "create" and parts[1] == "-group":
                    group_name = parts[2]
                    self._create_group(group_name)
                
                # Join group: join -group -groupname
                elif len(parts) >= 3 and parts[0] == "join" and parts[1] == "-group":
                    group_name = parts[2]
                    self._join_group(group_name)
                
                # Leave group: leave -group -groupname
                elif len(parts) >= 3 and parts[0] == "leave" and parts[1] == "-group":
                    group_name = parts[2]
                    self._leave_group(group_name)
                
                # Send group message: send -group -groupname
                elif len(parts) >= 3 and parts[0] == "send" and parts[1] == "-group":
                    group_name = parts[2]
                    self._send_group_message(group_name)
                
                # Show group messages: show -group -groupname
                elif len(parts) >= 3 and parts[0] == "show" and parts[1] == "-group":
                    group_name = parts[2]
                    self._show_group_messages(group_name)
                
                # List user groups: list -groups
                elif command.lower() == "list -groups":
                    self._list_user_groups()
                
                # Help
                elif command.lower() in ("h", "help", "-h", "--help", "?"):
                    self._show_help()

                # Short commands: u, g, m <name>, s <name>, h, q
                elif command.lower() == "u":
                    self._list_users()
                elif command.lower() == "g":
                    self._list_user_groups()
                elif len(parts) == 2 and parts[0].lower() in ("m", "open"):
                    self._open_chat(parts[1])
                elif len(parts) == 2 and parts[0].lower() == "s":
                    self._open_chat(parts[1])
                elif len(parts) == 1 and self.username:
                    self._open_chat(parts[0])
                
                else:
                    print("Unknown command. Type 'h' for help\n")
            
            except (KeyboardInterrupt, EOFError):
                self.running = False
            except Exception as e:
                print(f"Error: {e}\n")


if __name__ == "__main__":
    ChatApp()


