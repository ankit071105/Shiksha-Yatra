import torch
import torch.nn as nn
import cv2
import numpy as np
from PIL import Image

class GestureCNN(nn.Module):
    def __init__(self, num_classes=10):
        super(GestureCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.fc1 = nn.Linear(128 * 28 * 28, 512)
        self.fc2 = nn.Linear(512, num_classes)
        self.dropout = nn.Dropout(0.4)
        self.relu = nn.ReLU()
        self.bn1 = nn.BatchNorm2d(32)
        self.bn2 = nn.BatchNorm2d(64)
        self.bn3 = nn.BatchNorm2d(128)
        
    def forward(self, x):
        x = self.pool(self.relu(self.bn1(self.conv1(x))))
        x = self.pool(self.relu(self.bn2(self.conv2(x))))
        x = self.pool(self.relu(self.bn3(self.conv3(x))))
        x = x.view(-1, 128 * 28 * 28)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class GestureRecognizer:
    def __init__(self):
        self.model = GestureCNN()
        self.model.load_state_dict(torch.load('models/gesture_model.pth', map_location=torch.device('cpu')))
        self.model.eval()
        
        self.gestures = ['circle', 'square', 'triangle', 'star', 'heart', 
                        'thumbs_up', 'thumbs_down', 'peace', 'ok', 'point']
        
        self.transform = torchvision.transforms.Compose([
            torchvision.transforms.Resize((224, 224)),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                           std=[0.229, 0.224, 0.225])
        ])
    
    def preprocess_image(self, image):
        # Convert to PIL Image
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # Apply transformations
        image = self.transform(image).unsqueeze(0)
        return image
    
    def predict(self, image):
        # Preprocess image
        image_tensor = self.preprocess_image(image)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(image_tensor)
            _, predicted = torch.max(outputs, 1)
            gesture_idx = predicted.item()
            confidence = torch.nn.functional.softmax(outputs, dim=1)[0][gesture_idx].item()
        
        return self.gestures[gesture_idx], confidence