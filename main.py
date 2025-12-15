import subprocess
import sys
import time
from pathlib import Path

def main():
    """Start both Flask and Bot"""
    Path('templates').mkdir(exist_ok=True)
    
    print("🚀 TON Raffle System Starting...\n")
    
    # Start Flask in background
    print("🌐 Starting Flask web server on http://localhost:5000")
    flask_process = subprocess.Popen([sys.executable, 'web_app.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
    
    time.sleep(3)  # Give Flask time to start
    
    # Start Bot in foreground
    print("🤖 Starting Telegram bot...\n")
    try:
        bot_process = subprocess.run([sys.executable, 'bot.py'])
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        flask_process.terminate()
        flask_process.wait()
        sys.exit(0)

if __name__ == '__main__':
    main()