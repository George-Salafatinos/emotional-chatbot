// Global variable to track conversation context
let conversationId = null;

document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.querySelector('.typing-indicator');
    const emotionSvg = document.getElementById('emotion-svg');

    function getCurrentTime() {
        return new Date().toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }

    function updateEmotionalDisplay(emotionState) {
        // Update SVG face if provided
        if (emotionState.svg_face) {
            // Safely parse and update SVG
            const parser = new DOMParser();
            const svgDoc = parser.parseFromString(emotionState.svg_face, 'image/svg+xml');
            
            if (!svgDoc.querySelector('parsererror')) {
                // Clear existing content and set new SVG
                emotionSvg.innerHTML = '';
                emotionSvg.innerHTML = emotionState.svg_face;
            } else {
                console.error('Invalid SVG received:', emotionState.svg_face);
            }
        }

        // Update emotion stats
        const emotions = [
            { key: 'happiness', label: 'Happiness' },
            { key: 'energy', label: 'Energy' },
            { key: 'calmness', label: 'Calmness' },
            { key: 'confidence', label: 'Confidence' }
        ];

        emotions.forEach(({ key, label }) => {
            const statElement = document.querySelector(`.emotion-stat[data-emotion="${key}"]`);
            if (statElement) {
                const progressBar = statElement.querySelector('.progress');
                if (progressBar) {
                    const value = Math.max(0, Math.min(100, emotionState[key] || 50));
                    progressBar.style.width = `${value}%`;
                    
                    // Update color based on value
                    if (value >= 75) {
                        progressBar.style.backgroundColor = '#4CAF50';  // Green for high
                    } else if (value >= 25) {
                        progressBar.style.backgroundColor = '#FFA726';  // Orange for medium
                    } else {
                        progressBar.style.backgroundColor = '#EF5350';  // Red for low
                    }
                }
            }
        });
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Clear input and add user message
        messageInput.value = '';
        addMessage('user', message);
        
        // Show typing indicator and disable input
        typingIndicator.style.display = 'block';
        messageInput.disabled = true;
        sendButton.disabled = true;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Update conversation ID
            conversationId = data.conversation_id;

            // Add bot response
            addMessage('bot', data.response);

            // Update emotional display with new state
            if (data.emotion_state) {
                updateEmotionalDisplay({
                    ...data.emotion_state,
                    svg_face: data.svg_face
                });
            }

        } catch (error) {
            console.error('Error:', error);
            addMessage('bot', 'Sorry, there was an error processing your message.');
        } finally {
            // Hide typing indicator and re-enable input
            typingIndicator.style.display = 'none';
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
        }
    }

    function addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${role}-message`);
        
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.textContent = content;
        
        const messageTime = document.createElement('div');
        messageTime.classList.add('message-time');
        messageTime.textContent = getCurrentTime();
        
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageTime);
        
        // Add to chat messages and scroll to bottom
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Initialize with neutral emotional state
    updateEmotionalDisplay({
        primary_emotion: 'neutral',
        happiness: 50,
        energy: 50,
        calmness: 50,
        confidence: 50
    });
});