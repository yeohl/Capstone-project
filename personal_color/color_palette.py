import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from imutils import face_utils
import dlib


def create_diag_features(diag_file, n_colors=4):
    pc = PaletteCreator(n_colors)
    palette, lips, left_cheek, right_cheek = pc.create_palette(diag_file, save_paette=True)
    
    palette = np.array([palette], np.uint8)
    hsv_palette = cv2.cvtColor(palette, cv2.COLOR_BGR2HSV)
    lab_palette = cv2.cvtColor(palette, cv2.COLOR_BGR2LAB)

    mean_hsv = np.mean(hsv_palette, axis=1)[0]
    mean_lab = np.mean(lab_palette, axis=1)[0]
    
    skin = np.hstack([left_cheek, right_cheek])
    skin = skin.reshape(-1, 3)
    kmeans = KMeans(n_clusters=10, n_init=10, random_state=42)
    kmeans.fit(skin)
    skin_centers_ = kmeans.cluster_centers_
    skin_centers = np.array([skin_centers_], np.uint8)
    lab_palette = cv2.cvtColor(skin_centers, cv2.COLOR_BGR2LAB)
    mean_lab_skin = np.mean(lab_palette, axis=1)[0]
    skin_centers_ = np.mean(skin_centers_, axis=0)
    
    kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)
    lips = lips.reshape(-1, 3)
    kmeans.fit(lips)
    lips_centers = kmeans.cluster_centers_
    lips_centers = np.array([lips_centers], np.uint8)
    lab_palette = cv2.cvtColor(lips_centers, cv2.COLOR_BGR2LAB)
    mean_lab_lips = np.mean(lab_palette, axis=1)[0]
    
    img = cv2.imread(diag_file)
    h, w = img.shape[:2]
    face = pc.detector(img)[0]
    face = img[max(0, face.top()):min(face.bottom(), h), max(0, face.left()):min(face.right(), w)]
    face_l_var = pc.calculate_contrast(face)
    
    row = np.array([mean_lab_lips[1], face_l_var, mean_lab_skin[2], skin_centers_[0], mean_hsv, mean_lab])
    
    return row

class PaletteCreator:
    def __init__(self, n_colors=3):
        
        self.n_colors = n_colors

        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

        self.right_eye = None
        self.left_eye = None
        self.left_cheek = None
        self.right_cheek = None
        self.lips = None
        self.nose = None
        
    def save_palette(self, mean_colors):
        fig, axes = plt.subplots(1, len(mean_colors), figsize=(self.n_colors, 1))
        for ax, color in zip(axes, mean_colors):
            img = np.full((1, 1, 3), color, dtype=np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            ax.imshow(img)
            ax.axis('off')
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0,0)
        plt.savefig('images/palette.jpg', bbox_inches='tight', pad_inches=0)
        
    def calculate_contrast(self, img):
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray_image], [0], None, [256], [0, 256])
        hist /= hist.sum()
        mean = np.mean(hist)
        variance = np.mean((hist - mean) ** 2)
        return variance
        
    def extract_face_part(self, face_part_points):

        (x, y, w, h) = cv2.boundingRect(face_part_points)
        crop = self.img[y:y+h, x:x+w]
        
        # https://www.researchgate.net/publication/262371199_Explicit_image_detection_using_YCbCr_space_color_model_as_skin_detection
        # filter skin only (YCbCr)
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(crop, np.array([0, 133, 77]), np.array([255, 173, 127]))
        crop = cv2.bitwise_and(crop, crop, mask=mask)
        crop = cv2.cvtColor(crop, cv2.COLOR_YCrCb2BGR)

        crop = crop[~np.all(crop == [0, 135, 0], axis=-1)]
        crop = crop.reshape(((1, crop.shape[0], 3)))
        
        return crop


    def detect_face_part(self):
        face_parts = [[] for _ in range(len(face_utils.FACIAL_LANDMARKS_IDXS))]

        faces = self.detector(cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY), 1)
        
        if len(faces) == 0:
            return 0

        rect = faces[0]

        shape = self.predictor(cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY), rect)
        shape = face_utils.shape_to_np(shape)

        for idx, (_, (i, j)) in enumerate(face_utils.FACIAL_LANDMARKS_IDXS.items()):
            if idx not in [1, 3]:
                face_parts[idx] = shape[i:j]

        self.lips = self.extract_face_part(np.concatenate((shape[48:60], shape[60:68])))
        self.left_cheek = self.extract_face_part(np.concatenate((shape[29:33], shape[4:9])))
        self.right_cheek = self.extract_face_part(np.concatenate((shape[29:33], shape[10:15])))
        self.right_eye = self.extract_face_part(shape[36:42])
        self.left_eye = self.extract_face_part(shape[42:48])
        self.nose = self.extract_face_part(shape[27:36])

        return len(faces)
        
    def create_palette(self, image_path='image.jpg', save_palette=False):
        
        self.img = cv2.imread(image_path)
        
        if self.img is None:
            os.remove(image_path)
            return None
            
        yes_faces = self.detect_face_part()
        
        if not yes_faces:
            os.remove(image_path)
            return None
        
        stacked_images = np.hstack([self.right_eye, self.left_eye, self.lips, self.left_cheek, self.right_cheek, self.nose])
        stacked_images = stacked_images.reshape(-1, 3)
        
        if stacked_images.shape[0] == 0:
            os.remove(image_path)
            return None
            
        kmeans = KMeans(n_clusters=self.n_colors, n_init=10, random_state=42)
        kmeans.fit(stacked_images)

        cluster_centers = kmeans.cluster_centers_
        
        if save_palette:
            self.save_palette(cluster_centers)
        
        return cluster_centers, self.lips, self.left_cheek, self.right_cheek
