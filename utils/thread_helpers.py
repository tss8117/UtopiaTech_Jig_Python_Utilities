# ============================================================================
# JIG ONE v1.1 - Thread Helper Utilities
# ============================================================================

from threading import Thread, Event, Lock
from queue import Queue, Empty
from typing import Callable, Optional, Any
import time


class StoppableThread(Thread):
    """
    Thread with built-in stop mechanism.
    """
    
    def __init__(self, target: Callable = None, args: tuple = (), kwargs: dict = None):
        super().__init__(target=target, args=args, kwargs=kwargs or {}, daemon=True)
        self._stop_event = Event()
    
    def stop(self):
        """Signal the thread to stop"""
        self._stop_event.set()
    
    def stopped(self) -> bool:
        """Check if stop was requested"""
        return self._stop_event.is_set()
    
    def wait(self, timeout: float) -> bool:
        """Wait for timeout, return True if stop was signaled"""
        return self._stop_event.wait(timeout)


class PeriodicThread(Thread):
    """
    Thread that runs a function periodically.
    """
    
    def __init__(self, interval: float, target: Callable, args: tuple = ()):
        super().__init__(daemon=True)
        self.interval = interval
        self._target = target
        self._args = args
        self._stop_event = Event()
    
    def run(self):
        while not self._stop_event.is_set():
            try:
                self._target(*self._args)
            except Exception as e:
                print(f"[THREAD] Periodic thread error: {e}")
            
            self._stop_event.wait(self.interval)
    
    def stop(self):
        """Stop the periodic thread"""
        self._stop_event.set()


class MessageQueue:
    """
    Thread-safe message queue with callback support.
    """
    
    def __init__(self):
        self._queue: Queue = Queue()
        self._handlers: dict = {}
        self._processor_thread: Optional[Thread] = None
        self._stop_event = Event()
    
    def put(self, message_type: str, data: Any = None):
        """
        Put a message in the queue.
        
        Args:
            message_type: Type identifier for routing
            data: Message payload
        """
        self._queue.put((message_type, data))
    
    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a message type.
        
        Args:
            message_type: Type identifier
            handler: Callback function(data)
        """
        self._handlers[message_type] = handler
    
    def start_processing(self):
        """Start background message processing"""
        self._stop_event.clear()
        self._processor_thread = Thread(target=self._process_loop, daemon=True)
        self._processor_thread.start()
    
    def stop_processing(self):
        """Stop background message processing"""
        self._stop_event.set()
        self._queue.put(("__STOP__", None))  # Wake up the processor
        
        if self._processor_thread and self._processor_thread.is_alive():
            self._processor_thread.join(timeout=2.0)
    
    def _process_loop(self):
        """Background processing loop"""
        while not self._stop_event.is_set():
            try:
                message_type, data = self._queue.get(timeout=0.1)
                
                if message_type == "__STOP__":
                    break
                
                if message_type in self._handlers:
                    try:
                        self._handlers[message_type](data)
                    except Exception as e:
                        print(f"[QUEUE] Handler error for {message_type}: {e}")
                        
            except Empty:
                continue
    
    def process_pending(self):
        """Process all pending messages (for use with GUI mainloop)"""
        while True:
            try:
                message_type, data = self._queue.get_nowait()
                
                if message_type in self._handlers:
                    try:
                        self._handlers[message_type](data)
                    except Exception as e:
                        print(f"[QUEUE] Handler error for {message_type}: {e}")
                        
            except Empty:
                break


class ThreadSafeValue:
    """
    Thread-safe value wrapper.
    """
    
    def __init__(self, initial_value: Any = None):
        self._value = initial_value
        self._lock = Lock()
    
    def get(self) -> Any:
        """Get the value"""
        with self._lock:
            return self._value
    
    def set(self, value: Any):
        """Set the value"""
        with self._lock:
            self._value = value
    
    def compare_and_set(self, expected: Any, new_value: Any) -> bool:
        """Set value only if current value matches expected"""
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False


def run_in_thread(func: Callable, *args, **kwargs) -> Thread:
    """
    Run a function in a new daemon thread.
    
    Args:
        func: Function to run
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Started Thread object
    """
    thread = Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def run_after_delay(delay: float, func: Callable, *args, **kwargs):
    """
    Run a function after a delay.
    
    Args:
        delay: Delay in seconds
        func: Function to run
        *args, **kwargs: Arguments to pass to function
    """
    def delayed():
        time.sleep(delay)
        func(*args, **kwargs)
    
    Thread(target=delayed, daemon=True).start()
