# 🍃 FoodoraX — Turning Surplus into Smiles

### A Smart Food Surplus Redistribution Platform

FoodoraX is a web-based food redistribution platform designed to reduce food waste by connecting restaurants, college canteens, events, households, and other food donors with recipients and organizations that need food.

Our mission is simple: **Save Food. Reduce Waste. Share Smiles.**

---

## 📌 Problem Statement

Large amounts of edible food are wasted every day by restaurants, hostels, college canteens, events, and households, while many people and communities struggle to access food.

There is a need for a platform that makes surplus food easier to share, discover, and claim.

## 💡 Our Solution

FoodoraX provides a centralized platform where donors can list surplus food and recipients can explore available donations and claim suitable food items.

The platform aims to simplify food redistribution, encourage responsible food sharing, and support a more sustainable community.

---

## ✨ Key Features

- **User Authentication:** Registration and login for donors and recipients.
- **Role-Based Access:** Different functionality for donors, recipients, and administrators where enabled.
- **Food Donation Management:** Donors can add food listings with details such as category, quantity, expiry date, and pickup location.
- **Food Discovery:** Recipients can browse available food listings.
- **Food Claiming:** Recipients can claim available food donations.
- **Claim Notifications:** In-app notifications and email updates for food claim events, where configured.
- **Welcome Email:** Welcome emails for newly registered users, when email delivery is configured.
- **Expiry Management:** Expired food listings can be prevented from being claimed.
- **Pickup Information:** Food pickup details help donors and recipients coordinate collection.
- **QR Codes and PDF Reports:** Supporting QR-code and PDF-generation functionality.
- **Database Management:** SQLite database for local development.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Local database |
| HTML5 | Web page structure |
| CSS3 | Styling and responsive interface |
| Jinja2 | Dynamic HTML templates |
| Flask-Mail | Email notifications |
| QR Code Library | QR-code generation |
| ReportLab | PDF generation |
| Werkzeug | Password hashing and file utilities |

---

## 📂 Project Structure

```text
FoodoraX/
│
├── app.py
├── foodorax.db
├── requirements.txt
├── README.md
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── donate.html
│   └── ...
│
├── static/
│   ├── style.css
│   └── uploads/
│
└── .env
```

*Note: Your actual project may contain additional files or different template names. Update this structure to match your repository.*

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd FoodoraX
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual repository URL.

### 2. Create a Virtual Environment

**Windows:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, use the virtual environment's Python executable directly.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure `requirements.txt` contains the dependencies required by your application.

### 4. Configure Environment Variables

Create a local environment configuration file if your application uses environment variables.

Example:

```env
FOODORAX_EMAIL=your_email@gmail.com
FOODORAX_APP_PASSWORD=your_google_app_password
```

Use a Google App Password for Gmail SMTP when required. Never commit real credentials or secrets to GitHub.

### 5. Run the Application

```powershell
.\.venv\Scripts\python.exe app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

## 🧪 Testing Checklist

Before presenting the project, test these workflows:

- [ ] Register a new donor account.
- [ ] Register a new recipient account.
- [ ] Log in and log out successfully.
- [ ] Add a food donation as a donor.
- [ ] Confirm the listing appears for recipients.
- [ ] Claim an available food item.
- [ ] Verify the donation status and claim history.
- [ ] Check in-app notifications.
- [ ] Test welcome and claim emails when email configuration is enabled.
- [ ] Confirm expired food cannot be claimed.
- [ ] Check the application on desktop and mobile screen sizes.

---

## 🚀 Deployment

FoodoraX can be prepared for deployment on a suitable Python hosting platform.

Before deploying:

- Configure a persistent production database.
- Set email credentials through environment variables.
- Configure file uploads and persistent storage appropriately.
- Disable Flask debug mode in production.
- Test registration, login, donations, claims, and notifications on the live site.

**Important:** The current SQLite setup is intended for local development. SQLite files stored on ephemeral serverless filesystems may not persist reliably. Use a suitable persistent database for a production deployment.

---

## 🔮 Future Improvements

- Map integration for pickup locations.
- Improved food expiry reminders.
- More detailed donation and impact analytics.
- Enhanced mobile-friendly user experience.
- Production deployment with persistent database storage.

---

## 🌍 Social Impact

FoodoraX aims to:

- Reduce avoidable food waste.
- Make surplus food easier to discover and redistribute.
- Encourage responsible food-sharing practices.
- Connect donors with communities and organizations in need.
- Support a more sustainable and compassionate community.

---

## 👥 Team

**Team Name:** Code With Wolf  
**Project Name:** FoodoraX  
**Tagline:** Turning Surplus into Smiles

**Team Members**
- Vikash Singh
- Darshan Raghuvanshi
- Abhishek Yadav
- Ankit Kumar Verma
- Prakhar Chaubey

---

## 🎓 Project Information

Developed as an academic project to explore web development, database management, and technology-driven solutions for a real-world social problem.

---

## 📄 License

Choose a license before publishing this project publicly. If you want others to reuse and modify your code, consider adding an appropriate open-source license file.

---

### 💚 FoodoraX — Turning Surplus into Smiles

**Save Food. Reduce Waste. Share Smiles.**