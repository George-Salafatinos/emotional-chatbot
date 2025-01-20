# Emotional Chatbot

A simple Flask-based chatbot that displays emotions through dynamic SVG expressions. The bot maintains conversation context and visualizes its emotional state in real-time.

## Features

- Real-time chat interface
- Dynamic emotional expressions using SVG
- In-memory conversation history
- OpenAI gpt-4o-mini integration

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/emotional-chatbot.git
cd emotional-chatbot
```

2. Install dependencies:
```bash
pip install flask python-dotenv openai
```

3. Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to `http://localhost:5000`

## Project Structure

```
emotional-chatbot/
├── static/          # Static assets
│   ├── css/        # Stylesheets
│   └── js/         # JavaScript files
├── templates/      # Flask HTML templates
├── .env           # Environment variables (not in git)
└── app.py         # Main application
```

## Usage

1. Start the Flask server
2. Type messages in the chat interface
3. Watch the bot's emotional expression change based on the conversation

## Note

- Conversations are stored in memory and will reset when the server restarts
- You need a valid OpenAI API key to use the chatbot

## License

MIT License - feel free to use this code for your own projects!
