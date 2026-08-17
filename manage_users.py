import argparse
import sys
from app import app
from models import db, User

def create_user(username, email, password, fullname, role):
    with app.app_context():
        # Check if user already exists
        exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if exists:
            print(f"Error: User with username '{username}' or email '{email}' already exists.")
            return False
            
        user = User(username=username, email=email, full_name=fullname, role=role)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            print(f"Success: Registered user '{username}' with role '{role}'.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error saving user: {str(e)}")
            return False

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\n--- Registered Users ---")
        for u in users:
            status = "Active" if u.is_active_user else "Inactive"
            print(f"ID: {u.id} | Username: {u.username} | Email: {u.email} | Role: {u.role} | Name: {u.full_name} | Status: {status}")
        print("-" * 24)

def change_role(username, new_role):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            return False
        user.role = new_role
        try:
            db.session.commit()
            print(f"Success: Updated '{username}' role to '{new_role}'.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Hospital Management System CLI User Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # Subcommand: create
    create_parser = subparsers.add_parser("create", help="Create a new system user")
    create_parser.add_argument("--username", required=True, help="Unique username")
    create_parser.add_argument("--email", required=True, help="User email address")
    create_parser.add_argument("--password", required=True, help="User login password")
    create_parser.add_argument("--fullname", required=True, help="Full name of staff")
    create_parser.add_argument("--role", choices=["admin", "doctor", "nurse", "receptionist"], default="receptionist", help="System access role")
    
    # Subcommand: list
    subparsers.add_parser("list", help="List all registered system users")
    
    # Subcommand: role
    role_parser = subparsers.add_parser("role", help="Update user role")
    role_parser.add_argument("--username", required=True, help="Target username")
    role_parser.add_argument("--role", choices=["admin", "doctor", "nurse", "receptionist"], required=True, help="New system role")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_user(args.username, args.email, args.password, args.fullname, args.role)
    elif args.command == "list":
        list_users()
    elif args.command == "role":
        change_role(args.username, args.role)
    else:
        parser.print_help()
