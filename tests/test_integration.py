"""
Integration tests for the Mergington High School API backend.

Tests cover:
- Root endpoint (redirect to static files)
- Activities listing endpoint
- Student signup functionality
- Student unregister functionality
- Error handling and validation
"""

import pytest


class TestRootEndpoint:
    """Tests for the GET / root endpoint."""

    def test_root_redirects_to_static_index(self, client):
        """Verify root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesListEndpoint:
    """Tests for the GET /activities endpoint."""

    def test_get_all_activities_returns_200(self, client, fresh_activities):
        """Verify /activities endpoint returns 200 with all activities."""
        response = client.get("/activities")
        assert response.status_code == 200

    def test_get_activities_returns_all_nine_activities(self, client, fresh_activities):
        """Verify response contains all 9 activities."""
        response = client.get("/activities")
        data = response.json()
        assert len(data) == 9
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Soccer Club",
            "Art Club",
            "Drama Club",
            "Debate Club",
            "Science Club",
        ]
        for activity_name in expected_activities:
            assert activity_name in data

    def test_get_activities_has_correct_structure(self, client, fresh_activities):
        """Verify each activity has required fields."""
        response = client.get("/activities")
        data = response.json()
        required_fields = {"description", "schedule", "max_participants", "participants"}
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data, dict)
            assert required_fields.issubset(activity_data.keys())
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_initial_participant_counts(self, client, fresh_activities):
        """Verify initial participant counts match expected values."""
        response = client.get("/activities")
        data = response.json()
        expected_participants = {
            "Chess Club": 2,
            "Programming Class": 2,
            "Gym Class": 2,
            "Basketball Team": 0,
            "Soccer Club": 0,
            "Art Club": 0,
            "Drama Club": 0,
            "Debate Club": 0,
            "Science Club": 0,
        }
        for activity_name, expected_count in expected_participants.items():
            assert len(data[activity_name]["participants"]) == expected_count


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_new_student_returns_200(self, client, fresh_activities):
        """Verify successful signup returns 200."""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "newstudent@mergington.edu"},
        )
        assert response.status_code == 200

    def test_signup_new_student_adds_to_participants(self, client, fresh_activities):
        """Verify signup actually adds student to participants list."""
        email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email},
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Basketball Team"]["participants"]

    def test_signup_returns_success_message(self, client, fresh_activities):
        """Verify signup response contains success message."""
        email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email},
        )
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Basketball Team" in data["message"]

    def test_signup_to_nonexistent_activity_returns_404(self, client, fresh_activities):
        """Verify signup to non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"},
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_student_returns_400(self, client, fresh_activities):
        """Verify duplicate signup returns 400 error."""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_duplicate_student_error_message(self, client, fresh_activities):
        """Verify error message for duplicate signup is descriptive."""
        email = "michael@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        data = response.json()
        assert "Student already signed up for this activity" == data["detail"]

    def test_multiple_students_can_signup_same_activity(self, client, fresh_activities):
        """Verify multiple different students can signup for same activity."""
        activity_name = "Basketball Team"
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu",
        ]
        for email in students:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email},
            )
            assert response.status_code == 200

        # Verify all were added
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity_name]["participants"]
        for email in students:
            assert email in participants
        assert len(participants) == 3

    def test_same_student_can_signup_for_different_activities(self, client, fresh_activities):
        """Verify same student can signup for multiple different activities."""
        email = "versatile_student@mergington.edu"
        activities_to_join = ["Chess Club", "Drama Club", "Science Club"]
        
        for activity_name in activities_to_join:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email},
            )
            assert response.status_code == 200

        # Verify student is in all activities
        activities_response = client.get("/activities")
        data = activities_response.json()
        for activity_name in activities_to_join:
            assert email in data[activity_name]["participants"]


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/signup endpoint."""

    def test_unregister_existing_student_returns_200(self, client, fresh_activities):
        """Verify unregistering an enrolled student returns 200."""
        email = "michael@mergington.edu"  # In Chess Club
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 200

    def test_unregister_removes_student_from_participants(self, client, fresh_activities):
        """Verify unregister actually removes student from participants."""
        email = "michael@mergington.edu"
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 200

        # Verify student was removed
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert email not in participants

    def test_unregister_returns_success_message(self, client, fresh_activities):
        """Verify unregister response contains success message."""
        email = "michael@mergington.edu"
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Chess Club" in data["message"]

    def test_unregister_from_nonexistent_activity_returns_404(self, client, fresh_activities):
        """Verify unregister from non-existent activity returns 404."""
        response = client.delete(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"},
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_nonexistent_student_returns_400(self, client, fresh_activities):
        """Verify unregistering a non-enrolled student returns 400."""
        email = "notstudent@mergington.edu"  # Not in any activity
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_nonexistent_student_error_message(self, client, fresh_activities):
        """Verify error message when unregistering non-enrolled student."""
        email = "notstudent@mergington.edu"
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        data = response.json()
        assert "Student not signed up for this activity" == data["detail"]

    def test_unregister_twice_returns_400_second_time(self, client, fresh_activities):
        """Verify unregistering same student twice fails on second attempt."""
        email = "michael@mergington.edu"
        
        # First unregister should succeed
        response1 = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response1.status_code == 200

        # Second unregister should fail
        response2 = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response2.status_code == 400
        assert "not signed up" in response2.json()["detail"]

    def test_unregister_only_removes_from_specified_activity(self, client, fresh_activities):
        """Verify unregister only removes from specified activity, not others."""
        email = "versatile@mergington.edu"
        
        # Sign up for multiple activities
        client.post("/activities/Chess Club/signup", params={"email": email})
        client.post("/activities/Drama Club/signup", params={"email": email})
        client.post("/activities/Science Club/signup", params={"email": email})
        
        # Unregister from one activity
        response = client.delete(
            "/activities/Drama Club/signup",
            params={"email": email},
        )
        assert response.status_code == 200
        
        # Verify removed from Drama Club but still in others
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email not in data["Drama Club"]["participants"]
        assert email in data["Chess Club"]["participants"]
        assert email in data["Science Club"]["participants"]


class TestDataIsolation:
    """Tests to verify data isolation between test cases."""

    def test_first_test_has_fresh_state(self, client, fresh_activities):
        """Verify first test gets fresh state."""
        response = client.get("/activities")
        data = response.json()
        # Basketball Team should start empty
        assert len(data["Basketball Team"]["participants"]) == 0

    def test_second_test_also_has_fresh_state(self, client, fresh_activities):
        """Verify second test also gets fresh state (separate from first test)."""
        response = client.get("/activities")
        data = response.json()
        # Basketball Team should still be empty in this separate test
        assert len(data["Basketball Team"]["participants"]) == 0

    def test_signup_in_one_test_doesnt_affect_other_tests(self, client, fresh_activities):
        """Verify signups in one test don't persist to other tests."""
        # Sign up a student
        client.post(
            "/activities/Basketball Team/signup",
            params={"email": "testuser@mergington.edu"},
        )
        
        # Verify they were added in this test
        response = client.get("/activities")
        data = response.json()
        assert "testuser@mergington.edu" in data["Basketball Team"]["participants"]
        assert len(data["Basketball Team"]["participants"]) == 1
