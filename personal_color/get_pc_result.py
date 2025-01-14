import dlib
import cv2
from imutils import face_utils
from color_palette import *
import numpy as np
import os
from tensorflow.keras.models import load_model
from sklearn.externals import joblib
import warnings
warnings.filterwarnings('ignore')

def get_pc_result(diag_file='photo.jpg', n_colors=4):

    wc_model = load_model('warm_cool.h5')
    warm_model = joblib.load('warm.pkl')
    cool_model = joblib.load('cool.pkl')

    features = create_diag_features(diag_file, n_colors)
    wc_result = wc_model.predict(features)
    
    if wc_result == 0:
        result = cool_model.predict(features)
    else:
        result = warm_model.predict(features)
        
    if wc_result == 0:
        if result == 0:
            result = 'sum'
        elif result == 1:
            result = 'win'
    elif wc_result == 1:
        if result == 0:
            result = 'spr'
        elif result == 1:
            result = 'fal'
    print('Diag result:', result)
    
    os.remove(diag_file)
    
    return result
