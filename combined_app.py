import os
import threading
import requests
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import requests


# Charger les ressources nécessaires pour le serveur FastAPI
#model = joblib.load("server/model.pkl")
#metrics = joblib.load("server/metrics.pkl")
#feature_names = joblib.load("server/feature_names.pkl")

# Définir un chemin absolu basé sur le répertoire racine
file_path = os.path.join("server", "metrics.pkl")
metrics = joblib.load(file_path)

# Définir un chemin absolu basé sur le répertoire racine
file_path1 = os.path.join("server", "model.pkl")
model = joblib.load(file_path1)

# Définir un chemin absolu basé sur le répertoire racine
file_path2 = os.path.join("server", "feature_names.pkl")
feature_names = joblib.load(file_path2)


# ---------------------------------------------
# Configuration FastAPI
# ---------------------------------------------
fastapi_app = FastAPI()

# Autoriser les requêtes CORS pour Streamlit
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permettre les requêtes de toutes origines
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Schéma pour la requête de prédiction
class PredictionRequest(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float


@fastapi_app.post("/predict/")
def predict(request: PredictionRequest):
    input_data = [
        request.sepal_length,
        request.sepal_width,
        request.petal_length,
        request.petal_width,
    ]
    prediction = model.predict([input_data])[0]
    class_name = {0: "Setosa", 1: "Versicolor", 2: "Virginica"}
    return {"prediction": class_name[prediction]}


@fastapi_app.get("/metrics/")
def get_metrics():
    # Debug : Afficher les métriques avant de les renvoyer
    print("Metrics loaded:", metrics)
    
    try:
        return metrics
    except Exception as e:
        return {"error": f"Error retrieving metrics: {e}"}


# Fonction pour démarrer FastAPI
def start_fastapi():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)


# ---------------------------------------------
# Configuration Streamlit
# ---------------------------------------------
# URL de l'API FastAPI
API_URL = "http://localhost:8000"

# Fonction pour afficher la page de prédiction
def prediction_page():
    st.title("Iris Flower Predictor")
    st.write("Entrez les caractéristiques de la fleur pour prédire sa catégorie.")

    # Champs de saisie pour la prédiction
    sepal_length = st.number_input("Sepal Length", min_value=0.0, step=0.1)
    sepal_width = st.number_input("Sepal Width", min_value=0.0, step=0.1)
    petal_length = st.number_input("Petal Length", min_value=0.0, step=0.1)
    petal_width = st.number_input("Petal Width", min_value=0.0, step=0.1)

    if st.button("Prédire"):
        if all(v == 0.0 for v in [sepal_length, sepal_width, petal_length, petal_width]):
            st.error("Veuillez entrer des valeurs non nulles pour les caractéristiques.")
        else:
            payload = {
                "sepal_length": sepal_length,
                "sepal_width": sepal_width,
                "petal_length": petal_length,
                "petal_width": petal_width,
            }
            try:
                response = requests.post(f"{API_URL}/predict/", json=payload)
                if response.status_code == 200:
                    prediction = response.json()["prediction"]
                    st.success(f"La fleur prédite est : **{prediction}**")
                else:
                    st.error(f"Erreur API ({response.status_code}): {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")


# Fonction pour afficher la page des métriques


def metrics_page():
    st.title("Métriques d'apprentissage du modèle")

    try:
        # Envoyer la requête pour obtenir les métriques
        response = requests.get(f"{API_URL}/metrics/")

        if response.status_code == 200:
            # Récupérer les métriques
            metrics = response.json()

            # Afficher l'accuracy
            st.subheader("Accuracy")
            accuracy = metrics.get("accuracy", "Non disponible")
            if accuracy != "Non disponible":
                st.write(f"Accuracy: {accuracy:.2f}")
            else:
                st.warning("L'accuracy n'est pas disponible.")

            # Afficher le classification report
            st.subheader("Classification Report")
            classification_report = metrics.get("classification_report", "Non disponible")
            if classification_report != "Non disponible":
                st.text(classification_report)
            else:
                st.warning("Le rapport de classification n'est pas disponible.")

            # Afficher AUC ROC
            st.subheader("AUC ROC")
            auc_values = metrics.get("roc_auc", [])
            if auc_values:
                for i, auc in enumerate(auc_values):
                    st.write(f"AUC ROC for class {i}: {auc:.2f}")
            else:
                st.warning("Les valeurs AUC ROC ne sont pas disponibles.")

            # Afficher la courbe ROC
            st.subheader("Courbe ROC")
            fpr_values = metrics.get("fpr", [])
            tpr_values = metrics.get("tpr", [])
            auc_values = metrics.get("roc_auc", [])
            if fpr_values and tpr_values and auc_values:
                for i, (fpr, tpr, auc) in enumerate(zip(fpr_values, tpr_values, auc_values)):
                    fig, ax = plt.subplots()
                    ax.plot(fpr, tpr, label=f"Class {i} (AUC = {auc:.2f})")
                    ax.plot([0, 1], [0, 1], "k--")
                    ax.set_xlim([0.0, 1.0])
                    ax.set_ylim([0.0, 1.05])
                    ax.set_xlabel('False Positive Rate')
                    ax.set_ylabel('True Positive Rate')
                    ax.legend(loc='lower right')
                    st.pyplot(fig)
            else:
                st.warning("Les données pour les courbes ROC sont manquantes.")

            # Afficher la courbe Precision-Recall
            st.subheader("Courbe Precision-Recall")
            recall_values = metrics.get("recall", [])
            precision_values = metrics.get("precision", [])
            pr_auc_values = metrics.get("pr_auc", [])
            if recall_values and precision_values and pr_auc_values:
                for i, (recall, precision, pr_auc) in enumerate(zip(recall_values, precision_values, pr_auc_values)):
                    fig, ax = plt.subplots()
                    ax.plot(recall, precision, label=f"Class {i} (PR AUC = {pr_auc:.2f})")
                    ax.set_xlim([0.0, 1.0])
                    ax.set_ylim([0.0, 1.05])
                    ax.set_xlabel('Recall')
                    ax.set_ylabel('Precision')
                    ax.legend(loc='lower left')
                    st.pyplot(fig)
            else:
                st.warning("Les données pour les courbes Precision-Recall sont manquantes.")
        else:
            st.error(f"Erreur API ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {e}")


# ---------------------- Gestion de la navigation ----------------------
# Ajouter les boutons dans la barre latérale pour changer de page
if "current_page" not in st.session_state:
    st.session_state.current_page = "Prédiction"  # Page par défaut

# Utilisation de st.radio pour la navigation entre les pages
page = st.sidebar.radio("Aller à", ["Prédiction", "Métriques"])

# Mise à jour de la page en fonction de la sélection de l'utilisateur
if page == "Prédiction":
    st.session_state.current_page = "Prédiction"
elif page == "Métriques":
    st.session_state.current_page = "Métriques"

# Afficher la page en fonction de l'état
if st.session_state.current_page == "Prédiction":
    prediction_page()
elif st.session_state.current_page == "Métriques":
    metrics_page()
    
    
