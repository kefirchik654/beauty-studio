
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BEAUTY STUDIO API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://beauty-studio-blush.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return {
        "status": "ok",
        "message": "BEAUTY STUDIO API работает"
    }


@app.get("/services")
async def services():
    return [
        {"id": 1, "name": "Мужская стрижка", "price": 900, "duration": 45},
        {"id": 2, "name": "Женская стрижка", "price": 1500, "duration": 60},
        {"id": 3, "name": "Окрашивание", "price": 3000, "duration": 90},
        {"id": 4, "name": "Укладка", "price": 1000, "duration": 45},
    ]
