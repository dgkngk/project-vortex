from fastapi import FastAPI

app = FastAPI(title="Project Vortex API")

@app.get("/")
async def root():
    return {"message": "Project Vortex Data Foundation API"}
