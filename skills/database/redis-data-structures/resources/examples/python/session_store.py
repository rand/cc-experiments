"""
Redis Session Store Example

Implements a web session store using Redis with automatic expiration.
"""

import json
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import redis


class SessionStore:
    """
    Redis-based session store with automatic expiration.

    Stores user sessions in Redis hashes with automatic TTL management.
    """

    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        """
        Initialize session store.

        Args:
            redis_client: Redis connection
            ttl: Session TTL in seconds (default: 1 hour)
        """
        self.redis = redis_client
        self.default_ttl = ttl

    def create_session(self, user_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            user_id: User identifier
            data: Optional session data

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_key = f"session:{session_id}"

        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "ip_address": data.get("ip_address", "") if data else "",
            "user_agent": data.get("user_agent", "") if data else "",
        }

        # Add custom data
        if data:
            for key, value in data.items():
                if key not in session_data:
                    session_data[key] = value

        # Store as hash
        self.redis.hset(session_key, mapping=session_data)
        self.redis.expire(session_key, self.default_ttl)

        print(f"[SessionStore] Created session {session_id} for user {user_id}")
        return session_id

    def get_session(self, session_id: str, extend: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            session_id: Session identifier
            extend: Whether to extend session TTL (default: True)

        Returns:
            Session data or None if not found
        """
        session_key = f"session:{session_id}"

        # Check if exists
        if not self.redis.exists(session_key):
            print(f"[SessionStore] Session {session_id} not found")
            return None

        # Get all session data
        session_data = self.redis.hgetall(session_key)

        if extend:
            # Update last activity and extend TTL
            self.redis.hset(session_key, "last_activity", datetime.now().isoformat())
            self.redis.expire(session_key, self.default_ttl)
            print(f"[SessionStore] Extended session {session_id}")

        print(f"[SessionStore] Retrieved session {session_id}")
        return session_data

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session identifier
            data: Data to update

        Returns:
            Success boolean
        """
        session_key = f"session:{session_id}"

        if not self.redis.exists(session_key):
            print(f"[SessionStore] Session {session_id} not found")
            return False

        # Update data
        self.redis.hset(session_key, mapping=data)

        # Update last activity
        self.redis.hset(session_key, "last_activity", datetime.now().isoformat())

        # Extend TTL
        self.redis.expire(session_key, self.default_ttl)

        print(f"[SessionStore] Updated session {session_id}")
        return True

    def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session (logout).

        Args:
            session_id: Session identifier

        Returns:
            Success boolean
        """
        session_key = f"session:{session_id}"
        result = self.redis.delete(session_key)

        if result:
            print(f"[SessionStore] Destroyed session {session_id}")
        else:
            print(f"[SessionStore] Session {session_id} not found")

        return bool(result)

    def get_user_sessions(self, user_id: str) -> list:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session IDs
        """
        sessions = []

        # Scan for user sessions
        for key in self.redis.scan_iter(match="session:*", count=100):
            session_data = self.redis.hgetall(key)
            if session_data.get("user_id") == user_id:
                session_id = key.split(":")[-1]
                sessions.append(session_id)

        print(f"[SessionStore] Found {len(sessions)} sessions for user {user_id}")
        return sessions

    def destroy_user_sessions(self, user_id: str) -> int:
        """
        Destroy all sessions for a user (logout from all devices).

        Args:
            user_id: User identifier

        Returns:
            Number of sessions destroyed
        """
        sessions = self.get_user_sessions(user_id)
        count = 0

        for session_id in sessions:
            if self.destroy_session(session_id):
                count += 1

        print(f"[SessionStore] Destroyed {count} sessions for user {user_id}")
        return count

    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        count = 0
        for _ in self.redis.scan_iter(match="session:*", count=100):
            count += 1
        return count


class ShoppingCartSession(SessionStore):
    """
    Session store with shopping cart functionality.

    Extends SessionStore to add cart-specific methods.
    """

    def add_to_cart(self, session_id: str, product_id: str,
                    quantity: int = 1, price: float = 0.0) -> bool:
        """
        Add item to shopping cart.

        Args:
            session_id: Session identifier
            product_id: Product identifier
            quantity: Quantity to add
            price: Product price

        Returns:
            Success boolean
        """
        cart_key = f"cart:{session_id}"

        # Get current cart
        cart_data = self.redis.hget(cart_key, product_id)

        if cart_data:
            # Update existing item
            item = json.loads(cart_data)
            item["quantity"] += quantity
            item["updated_at"] = datetime.now().isoformat()
        else:
            # Add new item
            item = {
                "product_id": product_id,
                "quantity": quantity,
                "price": price,
                "added_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        # Store item
        self.redis.hset(cart_key, product_id, json.dumps(item))

        # Set expiration same as session
        self.redis.expire(cart_key, self.default_ttl)

        print(f"[ShoppingCart] Added {quantity}x {product_id} to cart")
        return True

    def get_cart(self, session_id: str) -> Dict[str, Any]:
        """
        Get shopping cart contents.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary of cart items
        """
        cart_key = f"cart:{session_id}"
        cart_data = self.redis.hgetall(cart_key)

        cart = {}
        total = 0.0

        for product_id, item_data in cart_data.items():
            item = json.loads(item_data)
            cart[product_id] = item
            total += item["price"] * item["quantity"]

        return {
            "items": cart,
            "total": total,
            "item_count": len(cart)
        }

    def remove_from_cart(self, session_id: str, product_id: str) -> bool:
        """
        Remove item from cart.

        Args:
            session_id: Session identifier
            product_id: Product identifier

        Returns:
            Success boolean
        """
        cart_key = f"cart:{session_id}"
        result = self.redis.hdel(cart_key, product_id)

        if result:
            print(f"[ShoppingCart] Removed {product_id} from cart")
        else:
            print(f"[ShoppingCart] Item {product_id} not in cart")

        return bool(result)

    def clear_cart(self, session_id: str) -> bool:
        """
        Clear shopping cart.

        Args:
            session_id: Session identifier

        Returns:
            Success boolean
        """
        cart_key = f"cart:{session_id}"
        result = self.redis.delete(cart_key)

        if result:
            print(f"[ShoppingCart] Cleared cart")

        return bool(result)


def demo_basic_session():
    """Demonstrate basic session operations."""
    print("\n" + "=" * 60)
    print("Basic Session Store Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    store = SessionStore(redis_client, ttl=300)  # 5 minutes

    # Create session
    print("\n--- Create Session ---")
    session_id = store.create_session(
        user_id="user:1000",
        data={
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "username": "alice"
        }
    )
    print(f"Session ID: {session_id}")

    # Get session
    print("\n--- Get Session ---")
    session = store.get_session(session_id)
    print(f"Session data: {json.dumps(session, indent=2)}")

    # Update session
    print("\n--- Update Session ---")
    store.update_session(session_id, {"page_views": "5", "theme": "dark"})

    # Get updated session
    print("\n--- Get Updated Session ---")
    session = store.get_session(session_id)
    print(f"Session data: {json.dumps(session, indent=2)}")

    # Get without extending TTL
    print("\n--- Get Without Extending TTL ---")
    session = store.get_session(session_id, extend=False)

    # Check TTL
    ttl = redis_client.ttl(f"session:{session_id}")
    print(f"Session TTL: {ttl} seconds")

    # Destroy session
    print("\n--- Destroy Session ---")
    store.destroy_session(session_id)

    # Try to get destroyed session
    print("\n--- Try to Get Destroyed Session ---")
    session = store.get_session(session_id)
    print(f"Session data: {session}")


def demo_multiple_sessions():
    """Demonstrate multiple sessions per user."""
    print("\n" + "=" * 60)
    print("Multiple Sessions Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    store = SessionStore(redis_client)

    user_id = "user:2000"

    # Create multiple sessions (different devices)
    print("\n--- Create Multiple Sessions ---")
    session1 = store.create_session(
        user_id,
        {"device": "laptop", "ip_address": "192.168.1.100"}
    )
    print(f"Session 1 (laptop): {session1}")

    session2 = store.create_session(
        user_id,
        {"device": "phone", "ip_address": "192.168.1.101"}
    )
    print(f"Session 2 (phone): {session2}")

    session3 = store.create_session(
        user_id,
        {"device": "tablet", "ip_address": "192.168.1.102"}
    )
    print(f"Session 3 (tablet): {session3}")

    # Get all user sessions
    print("\n--- Get All User Sessions ---")
    sessions = store.get_user_sessions(user_id)
    print(f"Active sessions for {user_id}: {len(sessions)}")
    for sid in sessions:
        session_data = store.get_session(sid, extend=False)
        print(f"  - {sid[:8]}... (device: {session_data.get('device')})")

    # Logout from one device
    print("\n--- Logout from Phone ---")
    store.destroy_session(session2)

    # Get remaining sessions
    print("\n--- Get Remaining Sessions ---")
    sessions = store.get_user_sessions(user_id)
    print(f"Active sessions: {len(sessions)}")

    # Logout from all devices
    print("\n--- Logout from All Devices ---")
    count = store.destroy_user_sessions(user_id)
    print(f"Destroyed {count} sessions")


def demo_shopping_cart():
    """Demonstrate shopping cart session."""
    print("\n" + "=" * 60)
    print("Shopping Cart Session Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    store = ShoppingCartSession(redis_client)

    # Create session
    print("\n--- Create Session ---")
    session_id = store.create_session(
        user_id="user:3000",
        data={"username": "bob"}
    )
    print(f"Session ID: {session_id}")

    # Add items to cart
    print("\n--- Add Items to Cart ---")
    store.add_to_cart(session_id, "product:100", quantity=2, price=29.99)
    print("Added: 2x Product 100 ($29.99 each)")

    store.add_to_cart(session_id, "product:101", quantity=1, price=49.99)
    print("Added: 1x Product 101 ($49.99)")

    store.add_to_cart(session_id, "product:102", quantity=3, price=9.99)
    print("Added: 3x Product 102 ($9.99 each)")

    # Get cart
    print("\n--- View Cart ---")
    cart = store.get_cart(session_id)
    print(f"Items in cart: {cart['item_count']}")
    print(f"Total: ${cart['total']:.2f}")
    print("\nItems:")
    for product_id, item in cart['items'].items():
        subtotal = item['price'] * item['quantity']
        print(f"  {product_id}: {item['quantity']}x ${item['price']} = ${subtotal:.2f}")

    # Update quantity
    print("\n--- Update Quantity ---")
    store.add_to_cart(session_id, "product:100", quantity=1, price=29.99)
    print("Added 1 more of Product 100")

    cart = store.get_cart(session_id)
    print(f"New total: ${cart['total']:.2f}")

    # Remove item
    print("\n--- Remove Item ---")
    store.remove_from_cart(session_id, "product:101")
    print("Removed Product 101")

    cart = store.get_cart(session_id)
    print(f"Items in cart: {cart['item_count']}")
    print(f"New total: ${cart['total']:.2f}")

    # Clear cart
    print("\n--- Clear Cart ---")
    store.clear_cart(session_id)
    cart = store.get_cart(session_id)
    print(f"Items in cart: {cart['item_count']}")

    # Cleanup
    store.destroy_session(session_id)


def demo_session_expiration():
    """Demonstrate session expiration."""
    print("\n" + "=" * 60)
    print("Session Expiration Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    store = SessionStore(redis_client, ttl=5)  # 5 seconds for demo

    # Create session
    print("\n--- Create Session with 5s TTL ---")
    session_id = store.create_session(
        user_id="user:4000",
        data={"username": "charlie"}
    )
    print(f"Session ID: {session_id}")

    # Check TTL
    ttl = redis_client.ttl(f"session:{session_id}")
    print(f"Initial TTL: {ttl} seconds")

    # Wait 3 seconds
    print("\n--- Wait 3 seconds ---")
    time.sleep(3)

    # Access session (extends TTL)
    print("\n--- Access Session (extends TTL) ---")
    session = store.get_session(session_id, extend=True)
    ttl = redis_client.ttl(f"session:{session_id}")
    print(f"TTL after access: {ttl} seconds (extended)")

    # Wait 3 more seconds
    print("\n--- Wait 3 more seconds ---")
    time.sleep(3)

    # Check TTL
    ttl = redis_client.ttl(f"session:{session_id}")
    print(f"Current TTL: {ttl} seconds")

    # Wait for expiration
    print("\n--- Wait for expiration ---")
    time.sleep(ttl + 1)

    # Try to access expired session
    print("\n--- Try to Access Expired Session ---")
    session = store.get_session(session_id)
    print(f"Session data: {session} (expired)")


def demo_session_statistics():
    """Demonstrate session statistics."""
    print("\n" + "=" * 60)
    print("Session Statistics Demo")
    print("=" * 60)

    redis_client = redis.Redis(decode_responses=True)
    store = SessionStore(redis_client)

    # Create sessions for multiple users
    print("\n--- Create Sessions ---")
    sessions = []
    for i in range(10):
        user_id = f"user:{1000 + i}"
        session_id = store.create_session(
            user_id,
            {"device": "web", "browser": "Chrome"}
        )
        sessions.append(session_id)

    # Get statistics
    print("\n--- Session Statistics ---")
    total = store.get_session_count()
    print(f"Total active sessions: {total}")

    # Count sessions per user
    user_session_counts = {}
    for session_id in sessions[:5]:
        session_data = store.get_session(session_id, extend=False)
        user_id = session_data["user_id"]
        user_session_counts[user_id] = user_session_counts.get(user_id, 0) + 1

    print("\nSessions per user (sample):")
    for user_id, count in user_session_counts.items():
        print(f"  {user_id}: {count}")

    # Cleanup
    print("\n--- Cleanup ---")
    for session_id in sessions:
        store.destroy_session(session_id)

    print(f"Cleaned up {len(sessions)} sessions")


def main():
    """Run all demos."""
    try:
        demo_basic_session()
        demo_multiple_sessions()
        demo_shopping_cart()
        demo_session_expiration()
        demo_session_statistics()

        print("\n" + "=" * 60)
        print("All demos completed!")
        print("=" * 60)
    except redis.exceptions.ConnectionError:
        print("Error: Cannot connect to Redis. Make sure Redis is running.")
        print("Start Redis with: redis-server")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
