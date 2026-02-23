"""
Haptic Feedback Pattern Engine
BlackRoad OS - Haptic pattern composition and playback
"""

import sqlite3
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import math


@dataclass
class HapticPattern:
    """Haptic feedback pattern descriptor"""
    id: str
    name: str
    category: str  # notification, game, media, accessibility, navigation
    description: str = ""
    sequence: List[Dict] = field(default_factory=list)  # [{type, duration_ms, intensity, pause_after_ms}]
    duration_ms: int = 0
    intensity: float = 0.5
    repeat: int = 1


class HapticEngine:
    """Haptic pattern composition and playback engine"""
    
    VALID_CATEGORIES = {"notification", "game", "media", "accessibility", "navigation"}
    VALID_SEQUENCE_TYPES = {"pulse", "buzz", "tap", "rumble"}
    
    # Built-in preset patterns
    PRESETS = {
        "notification": {
            "name": "notification",
            "category": "notification",
            "description": "Subtle notification pulse",
            "sequence": [
                {"type": "pulse", "duration_ms": 50, "intensity": 0.6, "pause_after_ms": 50},
                {"type": "pulse", "duration_ms": 50, "intensity": 0.6, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "success": {
            "name": "success",
            "category": "notification",
            "description": "Success confirmation pattern",
            "sequence": [
                {"type": "pulse", "duration_ms": 100, "intensity": 0.8, "pause_after_ms": 50},
                {"type": "pulse", "duration_ms": 100, "intensity": 0.8, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "error": {
            "name": "error",
            "category": "notification",
            "description": "Error alert pattern",
            "sequence": [
                {"type": "buzz", "duration_ms": 200, "intensity": 1.0, "pause_after_ms": 100},
                {"type": "buzz", "duration_ms": 200, "intensity": 1.0, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "warning": {
            "name": "warning",
            "category": "notification",
            "description": "Warning pattern",
            "sequence": [
                {"type": "tap", "duration_ms": 75, "intensity": 0.7, "pause_after_ms": 75},
                {"type": "tap", "duration_ms": 75, "intensity": 0.7, "pause_after_ms": 75},
                {"type": "tap", "duration_ms": 75, "intensity": 0.7, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "heartbeat": {
            "name": "heartbeat",
            "category": "media",
            "description": "Heartbeat simulation",
            "sequence": [
                {"type": "pulse", "duration_ms": 100, "intensity": 0.8, "pause_after_ms": 100},
                {"type": "pulse", "duration_ms": 100, "intensity": 0.8, "pause_after_ms": 300}
            ],
            "repeat": 2
        },
        "engine_rev": {
            "name": "engine_rev",
            "category": "game",
            "description": "Engine revving effect",
            "sequence": [
                {"type": "rumble", "duration_ms": 200, "intensity": 0.5, "pause_after_ms": 50},
                {"type": "rumble", "duration_ms": 200, "intensity": 0.7, "pause_after_ms": 50},
                {"type": "rumble", "duration_ms": 200, "intensity": 0.9, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "rain": {
            "name": "rain",
            "category": "media",
            "description": "Rain drops effect",
            "sequence": [
                {"type": "tap", "duration_ms": 30, "intensity": 0.4, "pause_after_ms": 100},
                {"type": "tap", "duration_ms": 30, "intensity": 0.4, "pause_after_ms": 80},
                {"type": "tap", "duration_ms": 30, "intensity": 0.4, "pause_after_ms": 120}
            ],
            "repeat": 3
        },
        "typing": {
            "name": "typing",
            "category": "accessibility",
            "description": "Key press feedback",
            "sequence": [
                {"type": "tap", "duration_ms": 25, "intensity": 0.5, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "explosion": {
            "name": "explosion",
            "category": "game",
            "description": "Explosion impact",
            "sequence": [
                {"type": "rumble", "duration_ms": 300, "intensity": 1.0, "pause_after_ms": 100},
                {"type": "pulse", "duration_ms": 200, "intensity": 0.6, "pause_after_ms": 0}
            ],
            "repeat": 1
        },
        "gentle_tap": {
            "name": "gentle_tap",
            "category": "notification",
            "description": "Gentle single tap",
            "sequence": [
                {"type": "tap", "duration_ms": 50, "intensity": 0.3, "pause_after_ms": 0}
            ],
            "repeat": 1
        }
    }
    
    def __init__(self, db_path: str = "~/.blackroad/haptics.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._init_presets()
    
    def _init_db(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT,
                sequence TEXT NOT NULL,
                duration_ms INTEGER,
                intensity REAL,
                repeat INTEGER DEFAULT 1,
                created_at TEXT,
                preset BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                device TEXT,
                timestamp TEXT,
                duration_ms INTEGER,
                FOREIGN KEY(pattern_id) REFERENCES patterns(id)
            )
        """)
        
        self.conn.commit()
    
    def _init_presets(self):
        """Load preset patterns"""
        cursor = self.conn.cursor()
        for preset_name, preset_data in self.PRESETS.items():
            cursor.execute("SELECT id FROM patterns WHERE name = ?", (preset_name,))
            if not cursor.fetchone():
                pattern_id = f"preset_{preset_name}"
                cursor.execute("""
                    INSERT INTO patterns 
                    (id, name, category, description, sequence, duration_ms, intensity, repeat, preset)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    pattern_id,
                    preset_data["name"],
                    preset_data["category"],
                    preset_data["description"],
                    json.dumps(preset_data["sequence"]),
                    self._calculate_duration(preset_data["sequence"], preset_data.get("repeat", 1)),
                    0.5,
                    preset_data.get("repeat", 1)
                ))
        self.conn.commit()
    
    def _calculate_duration(self, sequence: List[Dict], repeat: int = 1) -> int:
        """Calculate total pattern duration"""
        total = sum(s.get("duration_ms", 0) + s.get("pause_after_ms", 0) for s in sequence)
        return total * repeat
    
    def create_pattern(self, name: str, category: str, sequence: List[Dict], 
                       description: str = "", repeat: int = 1) -> str:
        """Create a new haptic pattern"""
        if category not in self.VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        for step in sequence:
            if step.get("type") not in self.VALID_SEQUENCE_TYPES:
                raise ValueError(f"Invalid sequence type: {step.get('type')}")
        
        pattern_id = f"pattern_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp() * 1000) % 10000}"
        duration_ms = self._calculate_duration(sequence, repeat)
        now = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO patterns 
            (id, name, category, description, sequence, duration_ms, intensity, repeat, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pattern_id, name, category, description, json.dumps(sequence), 
              duration_ms, 0.5, repeat, now))
        self.conn.commit()
        
        return pattern_id
    
    def play(self, pattern_id: str, device: str = "default") -> Dict:
        """Simulate pattern playback"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sequence, duration_ms FROM patterns WHERE id = ?
        """, (pattern_id,))
        
        row = cursor.fetchone()
        if not row:
            return {"error": f"Pattern {pattern_id} not found"}
        
        sequence = json.loads(row[0])
        duration_ms = row[1]
        
        # Log playback
        cursor.execute("""
            INSERT INTO playback_log (pattern_id, device, timestamp, duration_ms)
            VALUES (?, ?, ?, ?)
        """, (pattern_id, device, datetime.now().isoformat(), duration_ms))
        self.conn.commit()
        
        # Generate timeline
        timeline = []
        current_time = 0
        for step in sequence:
            timeline.append({
                "time_ms": current_time,
                "type": step["type"],
                "duration_ms": step["duration_ms"],
                "intensity": step["intensity"]
            })
            current_time += step["duration_ms"] + step.get("pause_after_ms", 0)
        
        return {
            "pattern_id": pattern_id,
            "device": device,
            "total_duration_ms": duration_ms,
            "timeline": timeline
        }
    
    def compose(self, pattern_ids: List[str]) -> str:
        """Chain multiple patterns into one"""
        cursor = self.conn.cursor()
        combined_sequence = []
        total_duration = 0
        
        for pid in pattern_ids:
            cursor.execute("SELECT sequence, duration_ms FROM patterns WHERE id = ?", (pid,))
            row = cursor.fetchone()
            if row:
                combined_sequence.extend(json.loads(row[0]))
                total_duration += row[1]
        
        composed_id = f"composed_{int(datetime.now().timestamp() * 1000)}"
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO patterns 
            (id, name, category, description, sequence, duration_ms, intensity, repeat, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (composed_id, "Composed", "notification", "Composed pattern", 
              json.dumps(combined_sequence), total_duration, 0.5, 1, now))
        self.conn.commit()
        
        return composed_id
    
    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """Retrieve pattern details"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, name, category, description, sequence, duration_ms, intensity, repeat
            FROM patterns WHERE id = ?
        """, (pattern_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "sequence": json.loads(row[4]),
                "duration_ms": row[5],
                "intensity": row[6],
                "repeat": row[7]
            }
        return None
    
    def list_patterns(self, category: Optional[str] = None) -> List[Dict]:
        """List all patterns, optionally filtered by category"""
        cursor = self.conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT id, name, category, duration_ms, intensity
                FROM patterns WHERE category = ?
                ORDER BY name
            """, (category,))
        else:
            cursor.execute("""
                SELECT id, name, category, duration_ms, intensity
                FROM patterns ORDER BY name
            """)
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "duration_ms": row[3],
                "intensity": row[4]
            }
            for row in cursor.fetchall()
        ]
    
    def export_json(self, pattern_id: str) -> Dict:
        """Export pattern in device SDK format"""
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return {}
        
        return {
            "version": "1.0",
            "pattern": {
                "id": pattern["id"],
                "name": pattern["name"],
                "type": pattern["category"],
                "totalDuration": pattern["duration_ms"],
                "haptics": pattern["sequence"]
            }
        }
    
    def generate_from_audio(self, audio_path: str) -> str:
        """Mock: Convert audio amplitude envelope to haptic pulses"""
        # Simulated audio analysis - in reality would use audio library
        pattern_id = self.create_pattern(
            name=f"audio_{Path(audio_path).stem}",
            category="media",
            sequence=[
                {"type": "pulse", "duration_ms": 100, "intensity": 0.6, "pause_after_ms": 50},
                {"type": "pulse", "duration_ms": 150, "intensity": 0.8, "pause_after_ms": 50},
                {"type": "pulse", "duration_ms": 80, "intensity": 0.5, "pause_after_ms": 0}
            ],
            description=f"Generated from {audio_path}",
            repeat=1
        )
        return pattern_id
    
    def preset_patterns(self) -> Dict:
        """Get all 10 built-in preset patterns"""
        patterns = {}
        for name in self.PRESETS.keys():
            pattern = self.get_pattern(f"preset_{name}")
            if pattern:
                patterns[name] = pattern
        return patterns
    
    def close(self):
        """Close database"""
        if self.conn:
            self.conn.close()


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(description="Haptic Feedback Pattern Engine")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    list_cmd = subparsers.add_parser("list", help="List patterns")
    list_cmd.add_argument("--category", help="Filter by category")
    
    # Play command
    play_cmd = subparsers.add_parser("play", help="Play pattern")
    play_cmd.add_argument("pattern_id", help="Pattern ID")
    play_cmd.add_argument("--device", default="default", help="Target device")
    
    # Presets command
    subparsers.add_parser("presets", help="Show built-in presets")
    
    args = parser.parse_args()
    engine = HapticEngine()
    
    try:
        if args.command == "list":
            patterns = engine.list_patterns(args.category)
            for p in patterns:
                print(f"  {p['name']}: {p['duration_ms']}ms, intensity={p['intensity']}")
        
        elif args.command == "play":
            result = engine.play(args.pattern_id, args.device)
            if "error" in result:
                print(f"✗ {result['error']}")
            else:
                print(f"✓ Playing {args.pattern_id} on {args.device} ({result['total_duration_ms']}ms)")
        
        elif args.command == "presets":
            presets = engine.preset_patterns()
            for name, pattern in presets.items():
                print(f"  {name}: {pattern['duration_ms']}ms")
        
        else:
            parser.print_help()
    
    finally:
        engine.close()


if __name__ == "__main__":
    main()
