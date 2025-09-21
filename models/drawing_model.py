import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import google.generativeai as genai

class DrawingCNN(nn.Module):
    def __init__(self, num_classes=10):
        super(DrawingCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.fc1 = nn.Linear(128 * 12 * 12, 512)
        self.fc2 = nn.Linear(512, num_classes)
        self.dropout = nn.Dropout(0.5)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = self.pool(self.relu(self.conv3(x)))
        x = x.view(-1, 128 * 12 * 12)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class DrawingRecognizer:
    def __init__(self):
        self.model = DrawingCNN()
        self.model.load_state_dict(torch.load('models/drawing_model.pth', map_location=torch.device('cpu')))
        self.model.eval()
        
        self.classes = ['cat', 'dog', 'house', 'tree', 'car', 'flower', 'person', 'sun', 'ball', 'fish']
        
        # Initialize Gemini
        genai.configure(api_key="AIzaSyAJfb_OJUYSHneb288E7ecckDzxsy6Gxiw")
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        
        self.transform = transforms.Compose([
            transforms.Resize((96, 96)),
            transforms.Grayscale(),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])
    
    def predict(self, image):
        # Preprocess image
        image = self.transform(image).unsqueeze(0)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(image)
            _, predicted = torch.max(outputs, 1)
            class_idx = predicted.item()
            confidence = torch.nn.functional.softmax(outputs, dim=1)[0][class_idx].item()
        
        return self.classes[class_idx], confidence
    
    def describe_drawing(self, drawing_class):
        prompt = f"Describe a {drawing_class} in a way that would be educational for children. Keep it to 2 sentences."
        response = self.gemini_model.generate_content(prompt)
        return response.text