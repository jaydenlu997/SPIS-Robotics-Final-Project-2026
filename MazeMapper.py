import time
from Direction import CardDirs, Direction, CardinalDirection

class MazeNode:
    def __init__(self, node_id, x, y, image):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.image = image
        # Maps absolute cardinal direction (CardDirs) to neighbor node_id or status
        # Possible statuses: "UNEXPLORED", "WALL", or an integer node_id
        self.edges = {
            CardDirs.NORTH: "WALL",
            CardDirs.EAST: "WALL",
            CardDirs.SOUTH: "WALL",
            CardDirs.WEST: "WALL"
        }
        
    def get_unexplored_edges(self):
        return [heading for heading, status in self.edges.items() if status == "UNEXPLORED"]

class MazeMapper:
    def __init__(self, distance_threshold=2.0):
        self.nodes = {}  # node_id -> MazeNode
        self.next_node_id = 0
        
        self.current_node_id = -1
        self.heading = CardinalDirection(CardDirs.NORTH)
        
        # Odometry
        self.x = 0.0
        self.y = 0.0
        
        # DFS State
        # Stack of tuples: (source_node_id, heading_taken_from_source)
        self.dfs_stack = []
        
        # Error margin for assuming two physical coordinates might be the same node
        self.distance_threshold = distance_threshold
        
    def update_odometry(self, dt):
        """Called every frame we drive straight to update our (x, y) location."""
        if self.heading.direction == CardDirs.NORTH:
            self.y += dt
        elif self.heading.direction == CardDirs.SOUTH:
            self.y -= dt
        elif self.heading.direction == CardDirs.EAST:
            self.x += dt
        elif self.heading.direction == CardDirs.WEST:
            self.x -= dt
            
    def get_relative_direction(self, target_heading: CardDirs) -> Direction:
        """Converts an absolute heading (e.g. WEST) into a relative turn (e.g. LEFT) based on our current heading."""
        diff = (target_heading.value - self.heading.direction.value) % 4
        if diff == 0:
            return Direction.STRAIGHT
        elif diff == 1:
            return Direction.RIGHT
        elif diff == 2:
            return "U_TURN"
        elif diff == 3:
            return Direction.LEFT
            
    def get_absolute_heading(self, relative_turn: Direction) -> CardDirs:
        """Calculates what our absolute heading will be if we take a relative turn."""
        if relative_turn == Direction.STRAIGHT:
            return self.heading.direction
        elif relative_turn == Direction.RIGHT:
            return CardDirs((self.heading.direction.value + 1) % 4)
        elif relative_turn == Direction.LEFT:
            return CardDirs((self.heading.direction.value - 1) % 4)
        return self.heading.direction # fallback

    def find_nearby_nodes(self):
        """Returns a list of node_ids that are physically close to our current (x, y)."""
        nearby = []
        for node_id, node in self.nodes.items():
            dist = ((self.x - node.x)**2 + (self.y - node.y)**2)**0.5
            if dist < self.distance_threshold:
                nearby.append(node_id)
        return nearby

    def register_dead_end(self):
        """Called when NO_DETECTED threshold is reached. Mark current path as WALL and U-Turn."""
        print(f"[MAPPER] Dead end reached at roughly ({self.x:.1f}, {self.y:.1f}).")
        if self.current_node_id != -1:
            if len(self.dfs_stack) > 0:
                _, heading_taken = self.dfs_stack[-1]
                self.nodes[self.current_node_id].edges[heading_taken] = "WALL"
                
        return self._do_uturn()

    def _do_uturn(self):
        self.heading.direction = CardDirs((self.heading.direction.value + 2) % 4)
        return "U_TURN"

    def process_intersection(self, img, paths, match_places_orb_fn):
        """
        Core DFS Logic.
        Returns the relative Direction (LEFT, RIGHT, STRAIGHT) to take, or "U_TURN".
        """
        print(f"\n[MAPPER] Intersection detected at ({self.x:.1f}, {self.y:.1f}). Checking for loops...")
        
        matched_node_id = -1
        
        # 1. Look for nearby nodes
        nearby_candidates = self.find_nearby_nodes()
        if nearby_candidates:
            print(f"[MAPPER] Found {len(nearby_candidates)} nearby candidates. Running ORB...")
            for candidate_id in nearby_candidates:
                candidate_img = self.nodes[candidate_id].image
                if match_places_orb_fn(candidate_img, img):
                    matched_node_id = candidate_id
                    print(f"[MAPPER] ORB Match! We have returned to Node {matched_node_id}")
                    break
        else:
            print("[MAPPER] No nearby candidates. This is a new area.")

        arrival_heading = CardDirs((self.heading.direction.value + 2) % 4)
        
        if matched_node_id != -1:
            # We hit a LOOP or backtracked
            current_node = self.nodes[matched_node_id]
            
            if self.current_node_id != -1 and len(self.dfs_stack) > 0 and self.dfs_stack[-1][0] == self.current_node_id:
                heading_taken = self.dfs_stack[-1][1]
                self.nodes[self.current_node_id].edges[heading_taken] = matched_node_id
                current_node.edges[arrival_heading] = self.current_node_id
            
            # Correct odometry to prevent drift
            self.x = current_node.x
            self.y = current_node.y
            
            # Pop stack if we are just hitting a loop while exploring
            if len(self.dfs_stack) > 0 and self.dfs_stack[-1][0] == self.current_node_id:
                self.dfs_stack.pop()
                
            self.current_node_id = matched_node_id
            
            unexplored = current_node.get_unexplored_edges()
            if unexplored:
                next_heading = unexplored[0]
                print(f"[MAPPER] Node {current_node.node_id} has unexplored paths. Taking {next_heading.name}.")
                self.dfs_stack.append((current_node.node_id, next_heading))
                relative_turn = self.get_relative_direction(next_heading)
                self.heading.direction = next_heading
                return relative_turn
            else:
                print(f"[MAPPER] Node {current_node.node_id} fully explored. U-Turning to backtrack.")
                return self._do_uturn()
                
        else:
            # NEW INTERSECTION
            new_id = self.next_node_id
            self.next_node_id += 1
            print(f"[MAPPER] Creating NEW Node {new_id}")
            
            new_node = MazeNode(new_id, self.x, self.y, img)
            
            if self.current_node_id != -1:
                new_node.edges[arrival_heading] = self.current_node_id
                if len(self.dfs_stack) > 0 and self.dfs_stack[-1][0] == self.current_node_id:
                    heading_taken = self.dfs_stack[-1][1]
                    self.nodes[self.current_node_id].edges[heading_taken] = new_id
            
            for path in paths:
                if path in [Direction.LEFT, Direction.RIGHT, Direction.STRAIGHT]:
                    abs_heading = self.get_absolute_heading(path)
                    new_node.edges[abs_heading] = "UNEXPLORED"
                    
            self.nodes[new_id] = new_node
            self.current_node_id = new_id
            
            unexplored = new_node.get_unexplored_edges()
            if unexplored:
                next_heading = unexplored[0]
                print(f"[MAPPER] Exploring {next_heading.name} from Node {new_id}")
                self.dfs_stack.append((new_id, next_heading))
                relative_turn = self.get_relative_direction(next_heading)
                self.heading.direction = next_heading
                return relative_turn
            else:
                return self._do_uturn()
