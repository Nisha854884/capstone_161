python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

terminal 1:
cd backend (not sure)
uvicorn main:app --reload --port 8000

terminal 2:
cd frontend
npm run dev

to run test_pipeline:
run terminal 1
terminal 2:
cd backend
python test_pipeline.py