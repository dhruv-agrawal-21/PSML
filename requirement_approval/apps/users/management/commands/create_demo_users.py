from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users for testing the Requirement Approval System'

    def handle(self, *args, **options):
        users_created = 0
        
        # Demo users data
        demo_users = [
            # Finance Department Users
            {'username': 'finance_user1', 'email': 'gauravchandak235@gmail.com', 'first_name': 'Gaurav', 'last_name': 'Chandak', 'role': 'user', 'department': 'finance'},
            {'username': 'finance_user2', 'email': 'finance_user2@example.com', 'first_name': 'Jane', 'last_name': 'Finance', 'role': 'user', 'department': 'finance'},
            {'username': 'finance_user3', 'email': 'finance_user3@example.com', 'first_name': 'Jack', 'last_name': 'Finance', 'role': 'user', 'department': 'finance'},
            
            # Marketing Department Users
            {'username': 'marketing_user1', 'email': 'marketing_user1@example.com', 'first_name': 'Alice', 'last_name': 'Marketing', 'role': 'user', 'department': 'marketing'},
            {'username': 'marketing_user2', 'email': 'marketing_user2@example.com', 'first_name': 'Bob', 'last_name': 'Marketing', 'role': 'user', 'department': 'marketing'},
            {'username': 'marketing_user3', 'email': 'marketing_user3@example.com', 'first_name': 'Carol', 'last_name': 'Marketing', 'role': 'user', 'department': 'marketing'},
            
            # Sales Department Users
            {'username': 'sales_user1', 'email': 'sales_user1@example.com', 'first_name': 'David', 'last_name': 'Sales', 'role': 'user', 'department': 'sales'},
            {'username': 'sales_user2', 'email': 'sales_user2@example.com', 'first_name': 'Eve', 'last_name': 'Sales', 'role': 'user', 'department': 'sales'},
            {'username': 'sales_user3', 'email': 'sales_user3@example.com', 'first_name': 'Frank', 'last_name': 'Sales', 'role': 'user', 'department': 'sales'},
            
            # Technical Department Users
            {'username': 'technical_user1', 'email': 'technical_user1@example.com', 'first_name': 'George', 'last_name': 'Technical', 'role': 'user', 'department': 'technical'},
            {'username': 'technical_user2', 'email': 'technical_user2@example.com', 'first_name': 'Helen', 'last_name': 'Technical', 'role': 'user', 'department': 'technical'},
            {'username': 'technical_user3', 'email': 'technical_user3@example.com', 'first_name': 'Ian', 'last_name': 'Technical', 'role': 'user', 'department': 'technical'},
            
            # Department Heads
            {'username': 'finance_head', 'email': 'jeeadvance1810@gmail.com', 'first_name': 'Finance', 'last_name': 'Head', 'role': 'head', 'department': 'finance'},
            {'username': 'marketing_head', 'email': 'marketing_head@example.com', 'first_name': 'Ms', 'last_name': 'Marketing Head', 'role': 'head', 'department': 'marketing'},
            {'username': 'sales_head', 'email': 'sales_head@example.com', 'first_name': 'Mr', 'last_name': 'Sales Head', 'role': 'head', 'department': 'sales'},
            {'username': 'technical_head', 'email': 'technical_head@example.com', 'first_name': 'Dr', 'last_name': 'Technical Head', 'role': 'head', 'department': 'technical'},
            
            # Executives
            {'username': 'admin', 'email': 'supportforacgl@gmail.com', 'first_name': 'Admin', 'last_name': 'Support', 'role': 'admin', 'department': 'executive'},
            {'username': 'cfo', 'email': 'agrawaldhruvy@gmail.com', 'first_name': 'Dhruv', 'last_name': 'Agrawal', 'role': 'cfo', 'department': 'executive'},
            {'username': 'ceo', 'email': 'ceo@example.com', 'first_name': 'Chief', 'last_name': 'Executive Officer', 'role': 'ceo', 'department': 'executive'},
        ]
        
        password = 'demo123'
        
        for user_data in demo_users:
            if not CustomUser.objects.filter(username=user_data['username']).exists():
                CustomUser.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=password,
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role=user_data['role'],
                    department=user_data['department'],
                )
                users_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created user: {user_data['username']}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"✗ User already exists: {user_data['username']}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Demo users setup complete! {users_created} new users created.")
        )
        self.stdout.write(
            self.style.SUCCESS(f"✓ All users can log in with password: {password}")
        )
