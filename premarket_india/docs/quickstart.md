
python -m venv venv
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up env vars
cp .env.example .env
# Edit .env and add your Groq API key (get free at https://console.groq.com)

# Initialize database
python -c "from storage.database import init_db; init_db()"

# Backfill historical data (run once, takes 5-10 minutes)
python scripts/backfill_history.py

# Generate your first report!
python main.py
