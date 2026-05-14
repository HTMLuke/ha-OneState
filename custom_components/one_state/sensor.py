import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback, HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

_LOGGER = logging.getLogger(__name__)

# Constants for states
STATUS_OK = "OK"
STATUS_WARNING = "Warning"
STATUS_CRITICAL = "Critical"

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the OneState sensor from a config entry."""
    config = entry.data
    async_add_entities([OneStateSensor(hass, config, entry.entry_id)])

class OneStateSensor(SensorEntity):
    """Representation of a OneState Sensor."""

    def __init__(self, hass: HomeAssistant, config: dict, entry_id: str):
        self._hass = hass
        self._attr_name = config["hub_name"]
        self._attr_unique_id = f"onestate_{config['hub_id']}"
        self._conditions = config["states"]
        self._attr_native_value = STATUS_OK
        self._entry_id = entry_id

    @property
    def icon(self) -> str:
        """Return the icon based on the current state."""
        if self._attr_native_value == STATUS_CRITICAL:
            return "mdi:alert-decagram"
        if self._attr_native_value == STATUS_WARNING:
            return "mdi:alert"
        return "mdi:check-circle"

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added to Home Assistant."""
        entity_ids = [c["entity_id"] for c in self._conditions]
        
        # Subscribe to updates of all monitored entities
        self.async_on_remove(
            async_track_state_change_event(
                self._hass, entity_ids, self._update_state_callback
            )
        )
        self._calculate_state()

    @callback
    def _update_state_callback(self, event):
        """Update the state when a monitored entity changes."""
        self._calculate_state()
        self.async_write_ha_state()

    def _calculate_state(self) -> None:
        """Evaluate all conditions and determine the overall state."""
        new_status = STATUS_OK
        
        for condition in self._conditions:
            state_obj = self._hass.states.get(condition["entity_id"])
            
            # Skip if entity is not available or unknown
            if not state_obj or state_obj.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue
                
            current_val = state_obj.state
            target_val = condition["value"]
            operator = condition["operator"]
            
            if self._evaluate_condition(current_val, target_val, operator):
                # Map the action string to our internal status
                action = condition["action"].upper()
                
                if "Critical" in action:
                    new_status = STATUS_CRITICAL
                    break  # CRITICAL is the highest priority, stop checking
                elif "Warning" in action and new_status != STATUS_CRITICAL:
                    new_status = STATUS_WARNING
        
        self._attr_native_value = new_status

    def _evaluate_condition(self, current: str, target: str, operator: str) -> bool:
        """Helper to evaluate conditions with type safety."""
        try:
            # Try numeric comparison first
            c_float = float(current)
            t_float = float(target)
            
            if operator == "=": return c_float == t_float
            if operator == "!=": return c_float != t_float
            if operator == ">": return c_float > t_float
            if operator == "<": return c_float < t_float
            if operator == ">=": return c_float >= t_float
            if operator == "<=": return c_float <= t_float
        except ValueError:
            # Fallback to string comparison
            if operator == "=": return str(current) == str(target)
            if operator == "!=": return str(current) != str(target)
            
        return False