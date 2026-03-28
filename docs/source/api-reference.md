<!-- NOTE: If you change the title (API Reference), you must update the code
in wakepy-docs.js! -->
# API Reference

```{eval-rst}

Wakepy Modes
-------------

There are two different modes in wakepy: The ``keep.running`` and ``keep.presenting``. See the :ref:`wakepy-modes` for more detailed explanations what they do and the :ref:`user-guide-page` for examples.

.. autosummary::

    wakepy.keep.running
    wakepy.keep.presenting


.. autofunction:: wakepy.keep.running
.. autofunction:: wakepy.keep.presenting

Wakepy Core
------------
.. autoclass:: wakepy.Mode
    :members: enter,
              exit,
              name,
              result,
              method,
              active_method,
              used_method,
              active,
              methods_priority,
              activation_result,
              probe_all_methods,
    :member-order: bysource

.. autoclass:: wakepy.MethodInfo
    :members:

.. autoclass:: wakepy.ActivationResult
    :members:
    :inherited-members:
    :exclude-members: results
    :member-order: bysource

.. autofunction:: wakepy.current_mode
.. autofunction:: wakepy.global_modes
.. autofunction:: wakepy.modecount

.. autoclass:: wakepy.MethodActivationResult
    :members: method,
              success,
              method_name,
              mode_name,
              failure_stage,
              failure_reason,
    :member-order: bysource

.. autoclass:: wakepy.ProbingResults
    :members:
    :inherited-members:
    :exclude-members: results
    :member-order: bysource

.. autoclass:: wakepy.ActivationError
    :exclude-members: args, with_traceback

.. autoclass:: wakepy.ActivationWarning
    :exclude-members: args, with_traceback

.. autoclass:: wakepy.NoCurrentModeError
    :exclude-members: args, with_traceback

.. autoclass:: wakepy.ContextAlreadyEnteredError
    :members:

.. autoclass:: wakepy.ModeExit
    :exclude-members: args, with_traceback

.. autoclass:: wakepy.core.constants.PlatformType
  :members:
  :undoc-members:
  :member-order: bysource

.. autoclass:: wakepy.core.constants.IdentifiedPlatformType
  :members:
  :undoc-members:
  :member-order: bysource

.. autodata:: wakepy.core.platform.CURRENT_PLATFORM
  :no-value:

.. autoclass:: wakepy.ModeName
  :members:
  :undoc-members:
  :member-order: bysource

.. autoclass:: wakepy.Method
    :members:

Lifecycle Hooks
---------------
Lifecycle hooks are callables that execute at specific points in a Mode's lifecycle. There are two groups:

- **Mode hooks** (``before_enter``, ``after_enter``, ``before_exit``, ``after_exit``) — receive the :class:`~wakepy.Mode` instance
- **Result hooks** (``on_success``, ``on_fail``) — receive the :class:`~wakepy.ActivationResult` instance

**Type Aliases:**

.. class:: wakepy.ModeHook

    Type alias for mode hooks: ``Callable[[Mode], Any]``

    Used by: ``before_enter``, ``after_enter``, ``before_exit``, ``after_exit``

.. class:: wakepy.ResultHook

    Type alias for result hooks: ``Callable[[ActivationResult], Any]``

    Used by: ``on_success`` and ``on_fail`` (when set to a callable).

.. versionadded:: 2.0.0

   Lifecycle hooks were added in version 2.0.0.

DBus Adapter
-------------
DBus adapters are an advanced concept of wakepy. They would be used in such a case where one wants to use other D-Bus python library than the default (which is `jeepney <https://jeepney.readthedocs.io/>`_).

.. autoclass:: wakepy.DBusAdapter
    :members:

.. autoclass:: wakepy.core.DBusMethodCall
    :members:

.. autoclass:: wakepy.core.DBusMethod
    :members:
    :exclude-members: count, index

.. autoclass:: wakepy.JeepneyDBusAdapter
    :members:

```
