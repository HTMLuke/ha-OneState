from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

from . import DOMAIN


class OneStateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1
    _states: list[dict[str, str]]
    _hub_name: str | None = None

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._hub_name = user_input["hub_name"].strip()
            return await self.async_step_state()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("hub_name"): selector.TextSelector(
                        selector.TextSelectorConfig()
                    )
                }
            ),
        )

    async def async_step_state(self, user_input=None) -> FlowResult:
        if not hasattr(self, "_states"):
            self._states = []

        if user_input is not None:
            self._current_entity = user_input["entity_id"]
            return await self.async_step_state_condition()

        schema = vol.Schema(
            {
                vol.Required("entity_id"): selector.EntitySelector(),
            }
        )

        return self.async_show_form(
            step_id="state",
            data_schema=schema,
            description_placeholders={"count": str(len(self._states))},
        )

    async def async_step_state_condition(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._states.append(
                {
                    "entity_id": self._current_entity,
                    "operator": user_input["operator"],
                    "value": user_input["value"],
                    "action": user_input["action"],
                }
            )
            return await self.async_step_add_more()

        schema = vol.Schema(
            {
                vol.Required("entity_display", default=self._current_entity): selector.EntitySelector(
                    selector.EntitySelectorConfig(include_entities=[self._current_entity])
                ),
                vol.Required("operator", default="="): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["<", ">", "=", "!=", ">=", "<="],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("value"): selector.StateSelector(
                    selector.StateSelectorConfig(entity_id=self._current_entity)
                ),
                vol.Required("action", default="Set OneState to Warning"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Set OneState to Warning", "Set OneState to Critical"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        # Get entity name for description fallback (not strictly needed now, but good)
        state_obj = self.hass.states.get(self._current_entity)
        entity_name = state_obj.name if state_obj else self._current_entity

        return self.async_show_form(
            step_id="state_condition",
            data_schema=schema,
            description_placeholders={"entity": entity_name},
        )

    async def async_step_add_more(self, user_input=None) -> FlowResult:
        return self.async_show_menu(
            step_id="add_more",
            menu_options=["add_state", "finish"],
            description_placeholders={"count": str(len(self._states))},
        )

    async def async_step_add_state(self, user_input=None) -> FlowResult:
        return await self.async_step_state()

    async def async_step_finish(self, user_input=None) -> FlowResult:
        if not self._hub_name:
            return await self.async_step_user()

        hub_id = self._hub_name.lower().replace(" ", "_")
        
        # Unique ID setzen, um doppelte Hubs zu vermeiden
        await self.async_set_unique_id(f"{DOMAIN}_{hub_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=self._hub_name,
            data={
                "hub_id": hub_id,
                "hub_name": self._hub_name,
                "states": self._states
            },
        )