from fastapi import FastAPI, Query
import asyncio

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome my site"}

@app.get("/hello")
async def hello_world():
    await asyncio.sleep(2)
    return {"message": "hello world"}

@app.get("/goodbye")
async def goodbye_world():
    await asyncio.sleep(2)
    return {"message": "goodbye world"}

@app.get("/fast")
async def fast_response():
    return {"message": "fast response"}

def calculate_square(number: float) -> float:
    """Returns the square of the given number."""
    return number ** 2

@app.get("/square")
async def square(number: float = Query(..., description="The number to be squared")):
    result = calculate_square(number)
    return {"number": number, "square": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
