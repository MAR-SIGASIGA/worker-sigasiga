import redis

class ScoreboardController():
    def __init__(self, event_id, redis_client):
        self.event_id = event_id
        self.redis_client = redis_client
        self.status_key = f"{self.event_id}-scoreboard-timer_status"
    def set_teams(self):
        """Set local and visitor team names."""
        local_team = input("Enter local team name: ")
        visitor_team = input("Enter visitor team name: ")
        self.redis_client.set(f"{self.event_id}-scoreboard-local_team", local_team)
        self.redis_client.set(f"{self.event_id}-scoreboard-visitor_team", visitor_team)
        print("Teams updated successfully!")

    def set_timer(self):
        """Set timer value in minutes."""
        try:
            minutes = int(input("Enter timer value in minutes: "))
            milliseconds = minutes * 60 * 1000
            self.redis_client.set(f"{self.event_id}-scoreboard-timer", milliseconds)
            print(f"Timer set to {minutes} minutes!")
        except ValueError:
            print("Invalid input! Please enter a valid number.")
    def update_points(self, team, operation):
        """Update points for a team."""
        key = f"{self.event_id}-scoreboard-{team}_points"
        current_points = int(self.redis_client.get(key) or 0)
        if operation == "sum":
            new_points = current_points + 1
        else:  # operation == "min"
            new_points = max(0, current_points - 1)
        self.redis_client.set(key, new_points)
        print(f"{team.title()} points updated to: {new_points}")
    def toggle_timer(self):
        """Toggle timer status between play (1) and stop (0)."""
        current_status = int(self.redis_client.get(self.status_key) or 0)
        new_status = 0 if current_status == 1 else 1
        self.redis_client.set(self.status_key, new_status)
        status_text = "running" if new_status == 1 else "stopped"
        print(f"Timer status set to: {status_text}")
    def show_menu(self):
        """Display the control menu."""
        print("\nScoreboard Control Menu:")
        print("1. Set Teams")
        print("2. Set Timer")
        print("3. Sum Local Points")
        print("4. Min Local Points")
        print("5. Sum Visitor Points")
        print("6. Min Visitor Points")
        print("7. Toggle Timer Status")
        print("q. Quit")
    def start_controller(self):
        """Main control loop."""
        while True:
            self.show_menu()
            choice = input("\nEnter your choice: ").lower()
            if choice == 'q':
                break
            elif choice == '1':
                self.set_teams()
            elif choice == '2':
                self.set_timer()
            elif choice == '3':
                self.update_points("local", "sum")
            elif choice == '4':
                self.update_points("local", "min")
            elif choice == '5':
                self.update_points("visitor", "sum")
            elif choice == '6':
                self.update_points("visitor", "min")
            elif choice == '7':
                self.toggle_timer()
            else:
                print("Invalid choice! Please try again.")

if __name__ == "__main__":
    event_id = input("Enter event ID: ")
    controller = ScoreboardController(event_id, redis.Redis(host='localhost', port=31802, db=0))
    controller.start_controller()
