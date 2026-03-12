pendo_backend/
│
├── app/
│   ├── __init__.py
│   │
│   ├── config/
│   │   └── config.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── photo.py
│   │   ├── swipe.py
│   │   └── match.py
│   │
│   ├── schemas/
│   │   ├── user_schema.py
│   │   └── auth_schema.py
│   │
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   └── discovery_routes.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   └── discovery_service.py
│   │
│   ├── extensions/
│   │   ├── db.py
│   │   ├── jwt.py
│   │   └── socket.py
│   │
│   ├── utils/
│   │   └── firebase.py
│   │
│   └── sockets/
│       └── chat_socket.py
│
├── migrations/
│
├── tests/
│
├── .env/
├── .gitignore
├── requirements.txt
├── .env.example
├── manage.py
└── run.py