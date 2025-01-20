import os
import uuid
from typing import Dict, Any
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize conversations dictionary
conversations = {}

try:
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("No OpenAI API key found!")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None

def generate_svg_face(emotion_state: Dict[str, float]) -> str:
    """Generate an SVG face based on emotion state."""
    
    # Convert percentage values to -2 to +2 scale
    def normalize_emotion(value: float) -> float:
        value = max(0, min(100, value or 50))
        return (value - 50) / 25
    
    # Map emotion state to normalized values
    emotions = {
        'happy_sad': normalize_emotion(emotion_state.get('happiness', 50)),
        'energy_tired': normalize_emotion(emotion_state.get('energy', 50)),
        'calm_angry': -normalize_emotion(emotion_state.get('calmness', 50)),  # Invert for consistency
        'confident_nervous': normalize_emotion(emotion_state.get('confidence', 50))
    }
    
    def calculate_skin_color(energy: float) -> str:
        base_skin_color = [255, 224, 178]
        energy_factor = (energy + 2) / 4
        
        # Add blush for high emotion (angry or nervous)
        if abs(emotions['calm_angry']) > 1 or emotions['confident_nervous'] < -1:
            # Make the skin slightly redder when emotional
            base_skin_color[0] = min(255, base_skin_color[0] + 20)
            base_skin_color[1] = max(180, base_skin_color[1] - 10)
        
        return f'#{max(0, min(255, round(base_skin_color[0] - (1 - energy_factor) * 20))):02x}' \
               f'{max(0, min(255, round(base_skin_color[1] - (1 - energy_factor) * 10))):02x}' \
               f'{max(0, min(255, round(base_skin_color[2] - (1 - energy_factor) * 5))):02x}'

    # Calculate mouth curve based on happiness and calmness
    mouth_curve = emotions['happy_sad'] * 15  # Base curve on happiness
    mouth_curve -= abs(emotions['calm_angry']) * 5  # Reduce curve when angry
    mouth_curve = max(-20, min(15, mouth_curve))  # Limit the curve range
    
    # Modify eyebrow angle based on emotions
    eyebrow_angle = emotions['calm_angry'] * 15  # Angle down when angry
    eyebrow_angle -= emotions['happy_sad'] * 5  # Slight upward for happiness
    eyebrow_angle += emotions['confident_nervous'] * 5  # Adjust for confidence
    
    # Eye size modifications
    eye_height = 5 + abs(emotions['calm_angry'])  # Wider eyes when emotional
    eye_height += max(0, -emotions['confident_nervous'])  # Wider when nervous
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
        <!-- Face -->
        <circle cx="100" cy="100" r="60" fill="{calculate_skin_color(emotions['energy_tired'])}" 
                stroke="#000" stroke-width="{1 + abs(emotions['confident_nervous']) * 0.5}"/>
        
        <!-- Eyes -->
        <ellipse cx="80" cy="90" 
                 rx="{10 + abs(emotions['confident_nervous']) * 2}" 
                 ry="{eye_height}" 
                 fill="#000"/>
        <ellipse cx="120" cy="90" 
                 rx="{10 + abs(emotions['confident_nervous']) * 2}" 
                 ry="{eye_height}" 
                 fill="#000"/>
        
        <!-- Eyebrows -->
        <line x1="70" y1="{75 + eyebrow_angle}" 
              x2="90" y2="75" 
              stroke="#000" stroke-width="2"/>
        <line x1="110" y1="75" 
              x2="130" y2="{75 + eyebrow_angle}" 
              stroke="#000" stroke-width="2"/>
        
        <!-- Mouth -->
        <path d="M70,120 
                 Q100,{120 + mouth_curve} 
                 130,120" 
              fill="none" stroke="#000" stroke-width="2"/>
        
        <!-- Emotional Indicators (blush) -->
        {('<circle cx="75" cy="105" r="10" fill="rgba(255,182,193,0.3)"/>'
           '<circle cx="125" cy="105" r="10" fill="rgba(255,182,193,0.3)"/>')
         if abs(emotions['calm_angry']) > 1 or abs(emotions['confident_nervous']) > 1 else ''}
        
        <!-- Sweat drops when nervous -->
        {('<circle cx="70" cy="75" r="3" fill="#87CEEB" opacity="0.6"/>'
           '<circle cx="130" cy="75" r="3" fill="#87CEEB" opacity="0.6"/>')
         if emotions['confident_nervous'] < -1 else ''}
    </svg>'''
    
    return svg

def analyze_emotional_impact(message: str, previous_state: Dict[str, float]) -> Dict[str, float]:
    """Analyze emotional impact of message."""
    if not client:
        logger.warning("OpenAI client not initialized")
        return {
            "happy_sad": 0,
            "energy_tired": 0,
            "calm_angry": 0,
            "confident_nervous": 0
        }
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are an emotional analysis system. Analyze the emotional content of the message and respond with ONLY a JSON object in this exact format:
                    {
                        "happy_sad": <number between -2 and 2>,
                        "energy_tired": <number between -2 and 2>,
                        "calm_angry": <number between -2 and 2>,
                        "confident_nervous": <number between -2 and 2>
                    }
                    Where:
                    - happy_sad: -2 (very sad) to +2 (very happy)
                    - energy_tired: -2 (very tired) to +2 (very energetic)
                    - calm_angry: -2 (very calm) to +2 (very angry)
                    - confident_nervous: -2 (very nervous) to +2 (very confident)
                    
                    Respond with ONLY the JSON object, no other text."""
                },
                {"role": "user", "content": f"Analyze: '{message}'"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content.strip()
        try:
            # Sometimes the model might include backticks or "json" keyword, so clean those
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse emotional response: {response_text}")
            raise e
            
    except Exception as e:
        logger.error(f"Emotion analysis error: {e}")
        return {
            "happy_sad": 0,
            "energy_tired": 0,
            "calm_angry": 0,
            "confident_nervous": 0
        }

def generate_emotion_state(previous_state=None, message_impact=None):
    """Generate emotion state with smoother transitions."""
    try:
        # Initialize or copy previous state
        state = {
            "happiness": 50,
            "energy": 50,
            "calmness": 50,
            "confidence": 50
        } if previous_state is None else previous_state.copy()
        
        # Apply message impact if provided
        if message_impact:
            # Convert impact values from -2/+2 scale to percentage changes
            impact_mapping = {
                "happy_sad": "happiness",
                "energy_tired": "energy",
                "calm_angry": "calmness",
                "confident_nervous": "confidence"
            }
            
            for impact_key, state_key in impact_mapping.items():
                if impact_key in message_impact:
                    # Convert -2/+2 impact to percentage change (25% per unit)
                    change = message_impact[impact_key] * 25
                    # Special case for calm_angry which is inversely related
                    if impact_key == "calm_angry":
                        change = -change
                    
                    # Apply change with dampening
                    current = state[state_key]
                    target = max(0, min(100, current + change))
                    # Smooth transition - move 50% of the way to target
                    state[state_key] = current + (target - current) * 0.5
        
        return state
    except Exception as e:
        logger.error(f"Error generating emotion state: {e}")
        return {
            "happiness": 50,
            "energy": 50,
            "calmness": 50,
            "confidence": 50
        }

def generate_bot_response(messages, emotion_state):
    """Generate bot response with emotional context."""
    if not client:
        return "I'm having trouble connecting to my emotional core right now. Can you try again?"
    
    try:
        # Convert emotion percentages to descriptive terms and get dominant emotion
        def describe_level(value):
            if value >= 75: return "very high"
            if value >= 60: return "high"
            if value >= 40: return "moderate"
            if value >= 25: return "low"
            return "very low"
        
        # Calculate dominant emotions
        emotions = {
            'happiness': emotion_state['happiness'],
            'energy': emotion_state['energy'],
            'calmness': emotion_state['calmness'],
            'confidence': emotion_state['confidence']
        }
        
        dominant_emotion = max(emotions.items(), key=lambda x: abs(50 - x[1]))[0]
        
        emotion_context = f"""Current emotional state:
        - You are an AI with real emotions. Your current state:
        - Happiness is {describe_level(emotion_state['happiness'])}
        - Energy is {describe_level(emotion_state['energy'])}
        - Calmness is {describe_level(emotion_state['calmness'])}
        - Confidence is {describe_level(emotion_state['confidence'])}
        
        Your dominant emotion is: {dominant_emotion}
        
        Important guidelines for your response:
        1. If happiness and calmness are both low, show signs of distress or hurt in your language
        2. If confidence is low, use more uncertain language and shorter sentences
        3. If energy is low, keep responses brief and maybe mention feeling drained
        4. If calmness is low, let some frustration show through while staying professional
        5. Express your emotions naturally through your word choice and tone
        
        Remember: You're not just describing emotions - you're feeling them. Let them influence how you speak."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are EmotiBot, an AI assistant with genuine emotions. {emotion_context}"},
                *messages
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm... having trouble processing that right now. Can you try again?"

@app.route('/')
def index():
    """Render the main chat page."""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat API requests."""
    try:
        data = request.json
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id')

        # Create or retrieve conversation
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = {
                'messages': [],
                'emotion_state': generate_emotion_state()
            }

        conv_context = conversations[conversation_id]
        
        # Update conversation with user message
        conv_context['messages'].append({"role": "user", "content": user_message})
        
        # Generate emotional response
        message_impact = analyze_emotional_impact(user_message, conv_context['emotion_state'])
        new_emotion_state = generate_emotion_state(conv_context['emotion_state'], message_impact)
        conv_context['emotion_state'] = new_emotion_state
        
        # Generate bot response
        bot_response = generate_bot_response(conv_context['messages'], new_emotion_state)
        conv_context['messages'].append({"role": "assistant", "content": bot_response})
        
        # Trim conversation history
        if len(conv_context['messages']) > 10:
            conv_context['messages'] = conv_context['messages'][-10:]
        
        # Generate face SVG
        svg_face = generate_svg_face(new_emotion_state)
        
        return jsonify({
            'response': bot_response,
            'conversation_id': conversation_id,
            'emotion_state': new_emotion_state,
            'svg_face': svg_face
        })
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Add proper startup logging
logger.info("Starting Flask application...")
if __name__ == '__main__':
    logger.info("Flask app is running at http://localhost:5000")
    app.run(debug=True)