"""Unit tests for the Google Calendar tools."""

from unittest.mock import MagicMock, patch

from tools.calendar_tool import list_calendar_events, create_calendar_event, NOT_CONNECTED_MSG


class TestNotConnected:
    """Both tools should fail gracefully when no token.json exists yet."""

    def test_list_events_when_not_connected(self):
        with patch("os.path.exists", return_value=False):
            result = list_calendar_events.invoke({})
        assert result == NOT_CONNECTED_MSG

    def test_create_event_when_not_connected(self):
        with patch("os.path.exists", return_value=False):
            result = create_calendar_event.invoke({
                "summary": "Test",
                "start_datetime": "2026-01-01T10:00:00",
                "end_datetime": "2026-01-01T11:00:00",
            })
        assert result == NOT_CONNECTED_MSG


class TestListCalendarEvents:
    """Test list_calendar_events with a mocked, already-connected service."""

    def test_lists_upcoming_events(self):
        fake_events = {
            "items": [
                {"summary": "Dentist", "start": {"dateTime": "2026-01-02T09:00:00Z"}},
                {"summary": "Team sync", "start": {"dateTime": "2026-01-03T14:00:00Z"}},
            ]
        }
        mock_service = MagicMock()
        mock_service.events.return_value.list.return_value.execute.return_value = fake_events

        with patch("tools.calendar_tool._get_calendar_service", return_value=mock_service):
            result = list_calendar_events.invoke({"days_ahead": 3})

        assert "Dentist" in result
        assert "Team sync" in result

    def test_no_upcoming_events(self):
        mock_service = MagicMock()
        mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}

        with patch("tools.calendar_tool._get_calendar_service", return_value=mock_service):
            result = list_calendar_events.invoke({"days_ahead": 5})

        assert "No upcoming events" in result

    def test_api_failure_is_handled_gracefully(self):
        mock_service = MagicMock()
        mock_service.events.return_value.list.return_value.execute.side_effect = Exception("API down")

        with patch("tools.calendar_tool._get_calendar_service", return_value=mock_service):
            result = list_calendar_events.invoke({})

        assert "Failed to fetch calendar events" in result
        assert "API down" in result


class TestCreateCalendarEvent:
    """Test create_calendar_event with a mocked, already-connected service."""

    def test_creates_event(self):
        mock_service = MagicMock()
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "summary": "Lunch",
            "htmlLink": "https://calendar.google.com/event?id=abc",
        }

        with patch("tools.calendar_tool._get_calendar_service", return_value=mock_service):
            result = create_calendar_event.invoke({
                "summary": "Lunch",
                "start_datetime": "2026-01-05T12:00:00",
                "end_datetime": "2026-01-05T13:00:00",
                "description": "With the team",
            })

        assert "Lunch" in result
        assert "https://calendar.google.com/event?id=abc" in result
        inserted_body = mock_service.events.return_value.insert.call_args.kwargs["body"]
        assert inserted_body["summary"] == "Lunch"
        assert inserted_body["start"]["dateTime"] == "2026-01-05T12:00:00"

    def test_api_failure_is_handled_gracefully(self):
        mock_service = MagicMock()
        mock_service.events.return_value.insert.return_value.execute.side_effect = Exception("quota exceeded")

        with patch("tools.calendar_tool._get_calendar_service", return_value=mock_service):
            result = create_calendar_event.invoke({
                "summary": "X",
                "start_datetime": "2026-01-05T12:00:00",
                "end_datetime": "2026-01-05T13:00:00",
            })

        assert "Failed to create calendar event" in result
        assert "quota exceeded" in result
