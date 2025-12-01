"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    global activities
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_contains_correct_fields(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test signing up for an existing activity"""
        response = client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_increases_participant_count(self, client):
        """Test that signing up increases the participant count"""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Chess Club"]["participants"])
        
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Chess Club"]["participants"])
        
        assert final_count == initial_count + 1


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_existing_participant(self, client):
        """Test removing an existing participant from an activity"""
        email = "michael@mergington.edu"
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]
    
    def test_remove_participant_from_nonexistent_activity(self, client):
        """Test removing a participant from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent Club/participants/test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing a participant who isn't signed up for the activity"""
        response = client.delete("/activities/Chess Club/participants/notregistered@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Student not found in this activity"
    
    def test_remove_participant_decreases_count(self, client):
        """Test that removing a participant decreases the participant count"""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Chess Club"]["participants"])
        
        client.delete("/activities/Chess Club/participants/michael@mergington.edu")
        
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Chess Club"]["participants"])
        
        assert final_count == initial_count - 1


class TestIntegrationScenarios:
    """Integration tests for complete user workflows"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test the complete workflow of signing up and then removing a participant"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        get_response = client.get("/activities")
        assert email in get_response.json()[activity]["participants"]
        
        # Remove
        remove_response = client.delete(f"/activities/{activity}/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify removal
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multitask@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify both signups
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]
