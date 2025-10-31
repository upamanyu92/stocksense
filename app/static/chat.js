/**
 * Chat Widget JavaScript - AI Assistant for StockSense
 * Handles chat interactions, message display, and learning
 */

let chatOpen = false;
let conversationHistory = [];

/**
 * Toggle chat widget open/close
 */
function toggleChat() {
  const chatWidget = document.getElementById('chatWidget');
  chatOpen = !chatOpen;
  
  if (chatOpen) {
    chatWidget.classList.add('open');
    document.getElementById('chatInput').focus();
    
    // Hide notification badge when opening
    const badge = document.getElementById('chatNotificationBadge');
    if (badge) {
      badge.style.display = 'none';
    }
    
    // Load conversation history on first open
    if (conversationHistory.length === 0) {
      loadChatHistory();
    }
  } else {
    chatWidget.classList.remove('open');
  }
}

/**
 * Send chat message to AI agent
 */
async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  
  if (!message) {
    return;
  }
  
  // Clear input
  input.value = '';
  
  // Disable send button
  const sendBtn = document.getElementById('chatSendBtn');
  sendBtn.disabled = true;
  
  // Add user message to chat
  addChatMessage('user', message);
  
  // Show typing indicator
  const typingIndicator = document.getElementById('typingIndicator');
  typingIndicator.classList.add('active');
  
  try {
    // Send message to API
    const response = await fetch('/api/chat/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        context: {}
      })
    });
    
    const data = await response.json();
    
    // Hide typing indicator
    typingIndicator.classList.remove('active');
    
    if (data.success) {
      // Add agent response
      addChatMessage('agent', data.response, data.intent);
      
      // Store in history
      conversationHistory.push({
        message: message,
        response: data.response,
        intent: data.intent,
        timestamp: new Date().toISOString()
      });
    } else {
      addChatMessage('agent', data.message || 'I encountered an error. Please try again!', 'error');
    }
  } catch (error) {
    console.error('Chat error:', error);
    typingIndicator.classList.remove('active');
    addChatMessage('agent', 'I\'m having trouble connecting. Please check your connection and try again!', 'error');
  } finally {
    // Re-enable send button
    sendBtn.disabled = false;
    input.focus();
  }
}

/**
 * Add message to chat display
 */
function addChatMessage(type, message, intent = null) {
  const messagesContainer = document.getElementById('chatMessages');
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message ${type}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  // Format message with markdown-like syntax
  const formattedMessage = formatChatMessage(message);
  bubble.innerHTML = formattedMessage;
  
  const time = document.createElement('div');
  time.className = 'message-time';
  time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  messageDiv.appendChild(bubble);
  messageDiv.appendChild(time);
  messagesContainer.appendChild(messageDiv);
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Format chat message with basic markdown-like syntax
 * Only allows specific formatting - all HTML is escaped first
 */
function formatChatMessage(message) {
  // First, escape all HTML to prevent XSS
  message = escapeHtml(message);
  
  // Now apply our safe formatting
  // Convert **bold** to <strong>
  message = message.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  
  // Convert newlines to <br>
  message = message.replace(/\n/g, '<br>');
  
  // Convert bullet points
  message = message.replace(/^• (.+)$/gm, '<li>$1</li>');
  
  // Wrap consecutive list items in <ul>
  message = message.replace(/(<li>.*?<\/li>\s*)+/g, function(match) {
    return '<ul style="margin: 10px 0; padding-left: 20px;">' + match + '</ul>';
  });
  
  return message;
}

/**
 * Load chat history from server
 */
async function loadChatHistory() {
  try {
    const response = await fetch('/api/chat/history?limit=10');
    const data = await response.json();
    
    if (data.success && data.history && data.history.length > 0) {
      // Clear default message if history exists
      const messagesContainer = document.getElementById('chatMessages');
      // Keep only the welcome message
      
      // Add historical messages
      data.history.forEach(item => {
        if (item.message) {
          addChatMessage('user', item.message);
        }
        if (item.response) {
          addChatMessage('agent', item.response);
        }
      });
      
      conversationHistory = data.history;
    }
  } catch (error) {
    console.error('Error loading chat history:', error);
  }
}

/**
 * Handle Enter key in chat input
 */
document.addEventListener('DOMContentLoaded', function() {
  const chatInput = document.getElementById('chatInput');
  
  if (chatInput) {
    chatInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }
  
  // Show notification badge on page load to attract attention
  setTimeout(() => {
    const badge = document.getElementById('chatNotificationBadge');
    if (badge && !chatOpen) {
      badge.style.display = 'flex';
    }
  }, 2000);
});

/**
 * Get user preferences from chat agent
 */
async function getChatPreferences() {
  try {
    const response = await fetch('/api/chat/preferences');
    const data = await response.json();
    
    if (data.success) {
      return data.preferences;
    }
  } catch (error) {
    console.error('Error fetching chat preferences:', error);
  }
  return null;
}

/**
 * Get agent statistics
 */
async function getChatStats() {
  try {
    const response = await fetch('/api/chat/stats');
    const data = await response.json();
    
    if (data.success) {
      console.log('Chat Agent Stats:', data.stats);
      return data.stats;
    }
  } catch (error) {
    console.error('Error fetching chat stats:', error);
  }
  return null;
}

// Make functions available globally
window.toggleChat = toggleChat;
window.sendChatMessage = sendChatMessage;
window.getChatPreferences = getChatPreferences;
window.getChatStats = getChatStats;
