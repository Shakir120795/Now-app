# Now-App

A luxury e-commerce application with Flutter mobile frontend and FastAPI backend.

## Project Structure

\\\
Now-app/
├── backend/              # FastAPI Backend
│   ├── app/              # Application code
│   ├── migrations/       # Database migrations
│   ├── tests/            # Unit & integration tests
│   ├── requirements.txt  # Python dependencies
│   ├── Dockerfile        # Docker configuration
│   ├── .env              # Environment variables
│   └── README.md         # Backend documentation
│
├── frontend/             # Flutter Mobile App
│   ├── lib/              # Flutter source code
│   ├── pubspec.yaml      # Flutter dependencies
│   ├── android/          # Android configuration
│   ├── ios/              # iOS configuration
│   └── README.md         # Frontend documentation
│
└── README.md             # This file
\\\

## Quick Start

### Backend Setup
\\\ash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
\\\

### Frontend Setup
\\\ash
cd frontend
flutter pub get
flutter run
\\\

## Features

- **OTP-based Authentication**: Secure login with OTP verification
- **E-Commerce Core**: Products, cart, orders, payments
- **Admin Dashboard**: Management tools for products and orders
- **Multiple Payment Gateways**: Razorpay, PhonePe integration
- **Analytics**: Track sales and user behavior
- **Push Notifications**: Firebase Cloud Messaging

## Deployment

- Backend: Deployed on Render
- Frontend: Built as APK for Android

## License

MIT
