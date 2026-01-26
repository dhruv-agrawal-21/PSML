# MYSQL CREDENTIALS CONFIGURATION

## 📍 WHERE TO ENTER YOUR MYSQL CREDENTIALS:

### Main Configuration File:
**Path:** `c:\Dhruv\PSML\requirement_approval\.env`

### What to Edit in .env file:

```
DB_USER=root                    ← Change to your MySQL username
DB_PASSWORD=root                ← Change to your MySQL password  
DB_HOST=localhost               ← Change if MySQL is on different server
DB_PORT=3306                    ← Change if MySQL uses different port
```

---

## 🔧 THREE WAYS TO CONFIGURE:

### Option 1: Automatic Setup (EASIEST)
Run this batch file (it will ask you for credentials):
```
c:\Dhruv\PSML\requirement_approval\setup_mysql.bat
```

### Option 2: Manual Edit
1. Open this file in any text editor:
   `c:\Dhruv\PSML\requirement_approval\.env`

2. Update these 4 lines with YOUR credentials:
   - DB_USER
   - DB_PASSWORD
   - DB_HOST
   - DB_PORT

3. Save the file

### Option 3: Command Line (after Django setup)
Will show you later how to use environment variables

---

## 📋 QUICK CHECKLIST:

- [ ] Find your MySQL username (usually: root)
- [ ] Find your MySQL password
- [ ] Find your MySQL host (usually: localhost)
- [ ] Find your MySQL port (usually: 3306)
- [ ] Update the `.env` file with these values
- [ ] Run: `mysql -u root -p -e "SHOW DATABASES;"`
- [ ] If successful, proceed with `python manage.py migrate`

---

## ❓ NEED HELP FINDING CREDENTIALS?

If you don't know your MySQL credentials:

1. Try these common defaults:
   - Username: `root`
   - Password: `root` or `password` or blank
   - Host: `localhost`
   - Port: `3306`

2. Or check:
   - MySQL installation folder
   - Your system logs
   - If installed with XAMPP/WAMP, check their control panel

---

## 🚀 AFTER CONFIGURING:

Once you've entered your credentials in `.env`:

```powershell
cd c:\Dhruv\PSML\requirement_approval
python manage.py migrate
python manage.py create_demo_users
python manage.py runserver
```

Then visit: http://localhost:8000/login/

