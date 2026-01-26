# Requirement Approval System - Setup Guide

## Step 1: Configure MySQL Credentials

### Location of Configuration File:
**File Path:** `c:\Dhruv\PSML\requirement_approval\.env`

### Where to Enter Credentials:

Open the `.env` file and update these lines with your MySQL credentials:

```
# MySQL Database Configuration - ENTER YOUR CREDENTIALS HERE
DB_ENGINE=django.db.backends.mysql
DB_NAME=requirement_approval
DB_USER=root
DB_PASSWORD=root          ← ENTER YOUR MYSQL PASSWORD HERE
DB_HOST=localhost
DB_PORT=3306
```

---

## Step 2: Create MySQL Database

Before running Django, create the database in MySQL:

```sql
CREATE DATABASE requirement_approval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Or run this command in MySQL terminal:**
```
mysql -u root -p -e "CREATE DATABASE requirement_approval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## Step 3: Verify MySQL Connection

Test if credentials are correct:
```powershell
mysql -u root -p -e "SHOW DATABASES;"
```

If you see the list of databases, your credentials are correct!

---

## Credentials to Update in `.env` file:

| Field | Current Value | Your Value |
|-------|---------------|-----------|
| DB_USER | root | _____ |
| DB_PASSWORD | root | _____ |
| DB_HOST | localhost | _____ |
| DB_PORT | 3306 | _____ |

---

## Next Steps After Configuration:

1. Update `.env` file with your MySQL credentials
2. Run: `python manage.py makemigrations`
3. Run: `python manage.py migrate`
4. Run: `python manage.py create_demo_users`
5. Run: `python manage.py runserver`

---

## File Locations:

- **Settings File:** `config/settings.py` (reads from .env)
- **Database Config:** `.env` file in project root
- **Environment Template:** `.env.example`

