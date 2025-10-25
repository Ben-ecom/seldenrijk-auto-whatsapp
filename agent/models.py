"""
Pydantic Models for Agent 1 (Structured Extraction)

These models define the structured output that Agent 1 (Pydantic AI) will extract
from conversation history. They ensure type-safe, validated data for qualification scoring.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime


class LeadQualification(BaseModel):
    """
    Structured qualification data extracted by Agent 1 (Pydantic AI).

    This model is used as the `result_type` parameter when creating the Pydantic AI agent,
    ensuring type-safe extraction with runtime validation.
    """

    # ============ BASIC INFO ============
    full_name: str | None = Field(
        None,
        description="Full name of candidate extracted from conversation"
    )

    years_experience: int | None = Field(
        None,
        ge=0,
        le=50,
        description="Years of experience in the field (0-50)"
    )

    skills: list[str] = Field(
        default_factory=list,
        description="List of skills mentioned (e.g., ['knippen', 'kleuren', 'extensions'])"
    )

    availability: str | None = Field(
        None,
        description="Availability (e.g., 'fulltime', 'parttime', '32 uur per week')"
    )

    # ============ QUALIFICATION SCORES ============
    technical_score: int = Field(
        0,
        ge=0,
        le=40,
        description="Technical skills score (0-40 points)"
    )

    soft_skills_score: int = Field(
        0,
        ge=0,
        le=40,
        description="Soft skills score (0-40 points)"
    )

    experience_score: int = Field(
        0,
        ge=0,
        le=20,
        description="Experience score (0-20 points)"
    )

    overall_score: int = Field(
        0,
        ge=0,
        le=100,
        description="Overall qualification score (sum of all scores, 0-100)"
    )

    # ============ QUALIFICATION STATUS ============
    qualification_status: Literal["qualified", "disqualified", "pending_review"] = Field(
        "pending_review",
        description="Final qualification status based on thresholds"
    )

    disqualification_reason: str | None = Field(
        None,
        description="Reason for disqualification if status is 'disqualified'"
    )

    missing_info: list[str] = Field(
        default_factory=list,
        description="List of missing information needed (e.g., ['ervaring', 'beschikbaarheid'])"
    )

    # ============ METADATA ============
    extraction_confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of extraction (0.0-1.0)"
    )

    reasoning: str | None = Field(
        None,
        description="Explanation of how scores were calculated (for human review)"
    )

    @field_validator("overall_score", mode="after")
    @classmethod
    def validate_overall_score(cls, v: int, info) -> int:
        """
        Ensure overall_score equals sum of component scores.
        """
        technical = info.data.get("technical_score", 0)
        soft_skills = info.data.get("soft_skills_score", 0)
        experience = info.data.get("experience_score", 0)
        expected = technical + soft_skills + experience

        if v != expected:
            # Auto-correct if mismatch
            return expected
        return v

    @field_validator("qualification_status", mode="after")
    @classmethod
    def validate_status_logic(cls, v: str, info) -> str:
        """
        Ensure qualification status matches score thresholds:
        - >= 70 points: qualified
        - < 30 points: disqualified
        - 30-69 points: pending_review
        """
        overall = info.data.get("overall_score", 0)

        if overall >= 70 and v != "qualified":
            return "qualified"
        elif overall < 30 and v != "disqualified":
            return "disqualified"
        elif 30 <= overall < 70 and v != "pending_review":
            return "pending_review"

        return v


class ConversationMessage(BaseModel):
    """
    Single message in conversation history for Agent 1 input.
    """
    sender: Literal["candidate", "agent"] = Field(
        description="Who sent the message"
    )
    content: str = Field(
        description="Message content"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When message was sent"
    )


class ExtractionInput(BaseModel):
    """
    Input format for Agent 1 extraction endpoint.
    """
    lead_id: str = Field(
        description="UUID of the lead to extract data for"
    )
    conversation_history: list[ConversationMessage] = Field(
        description="Full conversation history to analyze"
    )
    job_context: str | None = Field(
        None,
        description="Job posting context (if lead asked about specific job)"
    )


class ExtractionResponse(BaseModel):
    """
    Response from Agent 1 extraction endpoint.
    """
    success: bool = Field(
        description="Whether extraction succeeded"
    )
    qualification: LeadQualification | None = Field(
        None,
        description="Extracted qualification data"
    )
    error: str | None = Field(
        None,
        description="Error message if extraction failed"
    )
    model_used: str = Field(
        default="gpt-4o-mini",
        description="Model used for extraction"
    )
    execution_time_ms: int = Field(
        description="Extraction execution time in milliseconds"
    )
