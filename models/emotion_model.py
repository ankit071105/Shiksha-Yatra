import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import StandardScaler
import google.generativeai as genai

class EmotionCNN(nn.Module):
    def __init__(self, num_classes=7):
        super(EmotionCNN, self).__init__()
        self.conv1 = nn.Conv1d(1, 32, kernel_size=5, stride=2)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=5, stride=2)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=5, stride=2)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, num_classes)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.relu(self.conv3(x))
        x = self.pool(x).squeeze(-1)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class EmotionRecognizer:
    def __init__(self):
        self.model = EmotionCNN()
        self.model.load_state_dict(torch.load('models/emotion_model.pth', map_location=torch.device('cpu')))
        self.model.eval()
        
        self.emotions = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
        
        # Initialize Gemini
        genai.configure(api_key="AIzaSyAJfb_OJUYSHneb288E7ecckDzxsy6Gxiw")
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Audio preprocessing
        self.sample_rate = 22050
        self.duration = 3  # seconds
        self.n_mfcc = 40
        
    def extract_features(self, audio_path):
        # Load audio file
        y, sr = librosa.load(audio_path, sr=self.sample_rate, duration=self.duration)
        
        # Extract MFCC features
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.n_mfcc)
        
        # Pad or truncate to fixed size
        if mfcc.shape[1] < 130:
            mfcc = np.pad(mfcc, ((0, 0), (0, 130 - mfcc.shape[1])), mode='constant')
        else:
            mfcc = mfcc[:, :130]
        
        # Normalize
        scaler = StandardScaler()
        mfcc = scaler.fit_transform(mfcc)
        
        return torch.FloatTensor(mfcc).unsqueeze(0).unsqueeze(0)
    
    def predict(self, audio_path):
        # Extract features
        features = self.extract_features(audio_path)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(features)
            _, predicted = torch.max(outputs, 1)
            emotion_idx = predicted.item()
            confidence = torch.nn.functional.softmax(outputs, dim=1)[0][emotion_idx].item()
        
        return self.emotions[emotion_idx], confidence
    
    def get_emotion_description(self, emotion):
        prompt = f"Explain the emotion {emotion} to a child in a simple and educational way. Provide 2-3 sentences about what this emotion feels like and when people might experience it."
        response = self.gemini_model.generate_content(prompt)
        return response.text