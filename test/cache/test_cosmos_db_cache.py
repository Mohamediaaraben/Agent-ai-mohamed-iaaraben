#!/usr/bin/env python3 -m pytest

import pickle
import unittest
from unittest.mock import MagicMock, patch

from autogen.cache.cosmos_db_cache import CosmosDBCache
from azure.cosmos.exceptions import CosmosResourceNotFoundError

class TestCosmosDBCache(unittest.TestCase):
    def setUp(self):
        self.seed = "test_seed"
        self.connection_string = "AccountEndpoint=https://example.documents.azure.com:443/;"
        self.database_id = "autogen_cache"
        self.container_id = "TestContainer"
        self.client = MagicMock()

    @patch("autogen.cache.cosmos_db_cache.CosmosClient.from_connection_string", return_value=MagicMock())
    def test_init(self, mock_from_connection_string):
        cache = CosmosDBCache.from_connection_string(
            self.seed, self.connection_string, self.database_id, self.container_id
        )
        self.assertEqual(cache.seed, self.seed)
        mock_from_connection_string.assert_called_with(self.connection_string)

    def test_get(self):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        cache = CosmosDBCache(self.seed, {
            "connection_string": self.connection_string,
            "database_id": self.database_id,
            "container_id": self.container_id,
            "client": self.client
        })
        cache.container.read_item.return_value = {"data": serialized_value}
        self.assertEqual(cache.get(key), value)
        cache.container.read_item.assert_called_with(item=key, partition_key=str(self.seed))

        cache.container.read_item.side_effect = CosmosResourceNotFoundError("Item not found")
        self.assertIsNone(cache.get(key, default=None))

    def test_set(self):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        cache = CosmosDBCache(self.seed, {
            "connection_string": self.connection_string,
            "database_id": self.database_id,
            "container_id": self.container_id,
            "client": self.client
        })
        cache.set(key, value)
        expected_item = {
            "id": key,
            "partitionKey": str(self.seed),
            "data": serialized_value
        }
        cache.container.upsert_item.assert_called_with(expected_item)

    def test_context_manager(self):
        with patch('autogen.cache.cosmos_db_cache.CosmosDBCache.close', MagicMock()) as mock_close:
            with CosmosDBCache(self.seed, {
                "connection_string": self.connection_string,
                "database_id": self.database_id,
                "container_id": self.container_id,
                "client": self.client
            }) as cache:
                self.assertIsInstance(cache, CosmosDBCache)
            mock_close.assert_called()

if __name__ == "__main__":
    unittest.main()
