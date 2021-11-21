from __future__ import annotations

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import TYPE_CHECKING, MutableMapping

import aioredis

from ..helpers import nativestr
from .commands import JSONCommands
from .decoders import bulk_of_jsons, decode_list

if TYPE_CHECKING:
    from aioredis.client import ResponseCallbackT
    from aioredis.connection import ConnectionPool


class JSON(JSONCommands):
    """
    Create a client for talking to json.

    :param decoder:
    :type json.JSONDecoder: An instance of json.JSONDecoder

    :param encoder:
    :type json.JSONEncoder: An instance of json.JSONEncoder
    """

    def __init__(
        self,
        client,
        version=None,
        decoder=JSONDecoder(),
        encoder=JSONEncoder(),
    ):
        """
        Create a client for talking to json.

        :param decoder:
        :type json.JSONDecoder: An instance of json.JSONDecoder

        :param encoder:
        :type json.JSONEncoder: An instance of json.JSONEncoder
        """
        # Set the module commands' callbacks
        self.MODULE_CALLBACKS = {
            "JSON.CLEAR": int,
            "JSON.DEL": int,
            "JSON.FORGET": int,
            "JSON.GET": self._decode,
            "JSON.MGET": bulk_of_jsons(self._decode),
            "JSON.SET": lambda r: r and nativestr(r) == "OK",
            "JSON.NUMINCRBY": self._decode,
            "JSON.NUMMULTBY": self._decode,
            "JSON.TOGGLE": self._decode,
            "JSON.STRAPPEND": self._decode,
            "JSON.STRLEN": self._decode,
            "JSON.ARRAPPEND": self._decode,
            "JSON.ARRINDEX": self._decode,
            "JSON.ARRINSERT": self._decode,
            "JSON.ARRLEN": self._decode,
            "JSON.ARRPOP": self._decode,
            "JSON.ARRTRIM": self._decode,
            "JSON.OBJLEN": self._decode,
            "JSON.OBJKEYS": self._decode,
            "JSON.RESP": self._decode,
            "JSON.DEBUG": self._decode,
        }

        self.client = client
        self.execute_command = client.execute_command
        self.MODULE_VERSION = version

        for key, value in self.MODULE_CALLBACKS.items():
            self.client.set_response_callback(key, value)

        self.__encoder__ = encoder
        self.__decoder__ = decoder

    def _decode(self, obj):
        """Get the decoder."""
        if obj is None:
            return obj

        try:
            x = self.__decoder__.decode(obj)
            if x is None:
                raise TypeError
            return x
        except TypeError:
            try:
                return self.__decoder__.decode(obj.decode())
            except AttributeError:
                return decode_list(obj)
        except (AttributeError, JSONDecodeError):
            return decode_list(obj)

    def _encode(self, obj):
        """Get the encoder."""
        return self.__encoder__.encode(obj)

    def pipeline(self, transaction=True, shard_hint=None):
        """Creates a pipeline for the JSON module, that can be used for executing
        JSON commands, as well as classic core commands.

        Usage example:

        r = redis.Redis()
        pipe = r.json().pipeline()
        pipe.jsonset('foo', '.', {'hello!': 'world'})
        pipe.jsonget('foo')
        pipe.jsonget('notakey')
        """
        p = Pipeline(
            connection_pool=self.client.connection_pool,
            response_callbacks=self.MODULE_CALLBACKS,
            transaction=transaction,
            shard_hint=shard_hint,
        )
        p._encode = self._encode
        p._decode = self._decode
        return p


class Pipeline(JSONCommands, aioredis.client.Pipeline):
    """Pipeline for the module."""

    def __init__(
        self,
        connection_pool: ConnectionPool,
        response_callbacks: MutableMapping[str | bytes, ResponseCallbackT],
        transaction: bool,
        shard_hint: str | None,
    ):
        aioredis.client.Pipeline.__init__(
            self,
            connection_pool=connection_pool,
            response_callbacks=response_callbacks,
            transaction=transaction,
            shard_hint=shard_hint,
        )
