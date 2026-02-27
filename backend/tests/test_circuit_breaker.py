# =============================================================================
# Circuit Breaker Test Suite
# =============================================================================
# Tests for the circuit breaker pattern implementation.
# =============================================================================

import pytest
import asyncio
import time
from unittest.mock import patch

from app.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    get_circuit,
    with_circuit_breaker,
    get_all_circuit_states,
    _circuits,
)


# =============================================================================
# Test CircuitBreaker basic state transitions
# =============================================================================


class TestCircuitBreakerStates:
    """Tests for circuit breaker state machine."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(name="test_init")
        assert cb.state == CircuitState.CLOSED

    def test_is_available_when_closed(self):
        cb = CircuitBreaker(name="test_avail")
        assert cb.is_available is True

    @pytest.mark.asyncio
    async def test_stays_closed_on_success(self):
        cb = CircuitBreaker(name="test_success")
        await cb.record_success()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(name="test_open", failure_threshold=3)
        for _ in range(3):
            await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_not_available_when_open(self):
        cb = CircuitBreaker(name="test_open_unavail", failure_threshold=2)
        for _ in range(2):
            await cb.record_failure()
        assert cb.is_available is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(
            name="test_half_open", failure_threshold=2, recovery_timeout=0.1
        )
        for _ in range(2):
            await cb.record_failure()
        assert cb.state == CircuitState.OPEN
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_allows_limited_calls(self):
        cb = CircuitBreaker(
            name="test_half_limited",
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )
        for _ in range(2):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_available is True

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(
            name="test_half_reopen", failure_threshold=2, recovery_timeout=0.1
        )
        for _ in range(2):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        await cb.record_failure()
        assert cb._state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_successes_close(self):
        cb = CircuitBreaker(
            name="test_half_close",
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )
        for _ in range(2):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        for _ in range(2):
            await cb.record_success()
        assert cb._state == CircuitState.CLOSED

    def test_reset(self):
        cb = CircuitBreaker(name="test_reset")
        cb._state = CircuitState.OPEN
        cb._failure_count = 5
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_below_threshold_stay_closed(self):
        cb = CircuitBreaker(name="test_below", failure_threshold=5)
        for _ in range(4):
            await cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        cb = CircuitBreaker(name="test_reset_count", failure_threshold=5)
        for _ in range(4):
            await cb.record_failure()
        await cb.record_success()
        assert cb._failure_count == 0


# =============================================================================
# Test Circuit Breaker Decorator
# =============================================================================


class TestCircuitBreakerDecorator:
    """Tests for the with_circuit_breaker decorator."""

    @pytest.mark.asyncio
    async def test_decorator_passes_through_on_success(self):
        @with_circuit_breaker("test_dec_success", failure_threshold=3)
        async def my_func():
            return "ok"

        result = await my_func()
        assert result == "ok"
        # Cleanup
        _circuits.pop("test_dec_success", None)

    @pytest.mark.asyncio
    async def test_decorator_raises_circuit_open_error(self):
        @with_circuit_breaker(
            "test_dec_open", failure_threshold=2, recovery_timeout=60
        )
        async def failing_func():
            raise ValueError("fail")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Now it should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            await failing_func()

        _circuits.pop("test_dec_open", None)

    @pytest.mark.asyncio
    async def test_decorator_records_failure_on_exception(self):
        @with_circuit_breaker("test_dec_fail", failure_threshold=5)
        async def bad_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await bad_func()

        circuit = get_circuit("test_dec_fail")
        assert circuit._failure_count >= 1
        _circuits.pop("test_dec_fail", None)


# =============================================================================
# Test get_circuit and get_all_circuit_states
# =============================================================================


class TestCircuitRegistry:
    """Tests for circuit registry functions."""

    def test_get_circuit_creates_new(self):
        name = "test_reg_new"
        circuit = get_circuit(name)
        assert isinstance(circuit, CircuitBreaker)
        assert circuit.name == name
        _circuits.pop(name, None)

    def test_get_circuit_returns_same_instance(self):
        name = "test_reg_same"
        c1 = get_circuit(name)
        c2 = get_circuit(name)
        assert c1 is c2
        _circuits.pop(name, None)

    def test_get_all_circuit_states(self):
        name = "test_reg_states"
        get_circuit(name)
        states = get_all_circuit_states()
        assert name in states
        assert states[name]["state"] == "closed"
        assert states[name]["is_available"] is True
        _circuits.pop(name, None)


# =============================================================================
# Test CircuitOpenError
# =============================================================================


class TestCircuitOpenError:
    """Tests for the CircuitOpenError exception."""

    def test_error_message(self):
        err = CircuitOpenError("my_service")
        assert "my_service" in str(err)
        assert err.circuit_name == "my_service"
