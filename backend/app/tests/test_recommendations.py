import asyncio
from types import SimpleNamespace

from app.services import recommendations


def _opportunity(title: str, **values):
    defaults = {
        "title": title,
        "organization": "Example Org",
        "description": None,
        "tags": None,
        "location": None,
        "is_remote": False,
        "stipend": None,
        "source": "remote_jobs",
    }
    return SimpleNamespace(**(defaults | values))


def test_profile_text_uses_career_and_education_fields():
    user = SimpleNamespace(
        target_roles="Product design",
        skills="Figma, user research",
        bio="I make accessible interfaces",
        college="Design school",
        location="Jaipur",
    )

    profile = recommendations._profile_text(user)

    assert "Career interests: Product design" in profile
    assert "Skills: Figma, user research" in profile
    assert "About: I make accessible interfaces" in profile
    assert "Education: Design school" in profile
    assert "Location: Jaipur" in profile


def test_profile_text_has_general_student_fallback():
    user = SimpleNamespace(target_roles=None, skills=None, bio=None, college=None, location=None)

    assert "student" in recommendations._profile_text(user).lower()


def test_opportunity_text_includes_context_without_contact_emails():
    opportunity = _opportunity(
        "Product design internship",
        organization="Example Studio",
        description="Design accessible mobile experiences.",
        tags="Figma, accessibility, email:recruiter@example.com",
        location="Remote",
        is_remote=True,
        stipend="$1,000",
    )

    text = recommendations._opportunity_text(opportunity)

    assert "Design accessible mobile experiences." in text
    assert "Figma, accessibility" in text
    assert "Remote role" in text
    assert "$1,000" in text
    assert "recruiter@example.com" not in text


def test_semantic_similarity_ranks_profile_relevant_role_first():
    user = SimpleNamespace(
        target_roles="Product design",
        skills="Figma, user research",
        bio="I make accessible interfaces",
        college=None,
        location=None,
    )
    design_role = _opportunity("Accessible product design internship")
    unrelated_role = _opportunity("Distributed database infrastructure engineer")
    vectors = {
        recommendations._profile_text(user): (1.0, 0.0),
        recommendations._opportunity_text(design_role): (0.95, 0.05),
        recommendations._opportunity_text(unrelated_role): (0.0, 1.0),
    }
    original_embed_texts = recommendations._embed_texts
    recommendations._embed_texts = lambda texts: [vectors[text] for text in texts]

    try:
        ranked = asyncio.run(recommendations.rank_opportunities(user, [unrelated_role, design_role], 2))
    finally:
        recommendations._embed_texts = original_embed_texts

    assert ranked == [design_role, unrelated_role]
