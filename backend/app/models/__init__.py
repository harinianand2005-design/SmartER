"""SQLAlchemy models for SmartER operational and auth data."""

from app.models.entities import (
	AIAssessment,
	Alert,
	ERMetric,
	ExternalFactor,
	ModelMetric,
	Prediction,
	Recommendation,
	ResourcePrediction,
	User,
	UserRole,
)

model_registry = (User, ERMetric, ExternalFactor, Prediction, ResourcePrediction, AIAssessment, Alert, Recommendation, ModelMetric)

__all__ = ["model_registry", "User", "UserRole", "ERMetric", "ExternalFactor", "Prediction", "ResourcePrediction", "AIAssessment", "Alert", "Recommendation", "ModelMetric"]