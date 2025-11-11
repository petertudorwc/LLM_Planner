import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  List,
  ListItem,
  Typography,
  CircularProgress,
} from '@mui/material';
import { Send as SendIcon, Mic as MicIcon } from '@mui/icons-material';
import { chatAPI, speechAPI } from '../services/api';
import { useMap } from '../contexts/MapContext';

function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const { addMapUpdate } = useMap();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(userMessage, messages);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.data.response },
      ]);
      
      // Handle map updates if present
      if (response.data.map_updates && response.data.map_updates.length > 0) {
        response.data.map_updates.forEach(update => {
          addMapUpdate(update);
        });
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: Failed to get response' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceInput = async () => {
    if (recording) {
      // Stop recording
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      setRecording(false);
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
          audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
          try {
            const response = await speechAPI.transcribe(audioBlob);
            setInput(response.data.text);
          } catch (error) {
            console.error('Error transcribing audio:', error);
          }
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        mediaRecorderRef.current = mediaRecorder;
        setRecording(true);
      } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Could not access microphone');
      }
    }
  };

  return (
    <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <Paper sx={{ flexGrow: 1, overflow: 'auto', p: 2, m: 2 }}>
        <List>
          {messages.map((message, index) => (
            <ListItem
              key={index}
              sx={{
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <Paper
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  bgcolor: message.role === 'user' ? 'primary.main' : 'grey.800',
                }}
              >
                <Typography variant="body1">{message.content}</Typography>
              </Paper>
            </ListItem>
          ))}
          {loading && (
            <ListItem>
              <CircularProgress size={24} />
            </ListItem>
          )}
          <div ref={messagesEndRef} />
        </List>
      </Paper>

      <Paper sx={{ p: 2, m: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <IconButton
            color={recording ? 'error' : 'primary'}
            onClick={handleVoiceInput}
          >
            <MicIcon />
          </IconButton>
          <IconButton color="primary" onClick={handleSend} disabled={loading || !input.trim()}>
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>
    </Box>
  );
}

export default ChatPanel;
