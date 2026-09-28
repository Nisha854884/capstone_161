from auth import init_auth_db, create_user

init_auth_db()

user = create_user(
    username="admin",
    password="admin123",
    role="admin"
)

if user:
    print("Admin created:")
    print(user)
else:
    print("Admin already exists.")