import json
import logging
from typing import TYPE_CHECKING
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import DEFAULT_ADDRESS_NAME_PRIORITY, Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _add_cache_table(write_cursor: 'DBCursor') -> None:
    """Add a new key-value cache table for this upgrade"""
    log.debug('Enter _add_cache_table')
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS key_value_cache (
        name TEXT NOT NULL PRIMARY KEY,
        value TEXT
    );""")
    log.debug('Exit _add_cache_table')


def _move_non_settings_mappings_to_cache(write_cursor: 'DBCursor') -> None:
    """Move the non-settings value from `settings` to a seperate `key_value_cache` table"""
    log.debug('Enter _move_non_settings_mappings_to_cache')
    settings_moved = (
        'last_balance_save',
        'last_data_upload_ts',
        'last_data_updates_ts',
        'last_owned_assets_update',
        'last_evm_accounts_detect_ts',
        'last_spam_assets_detect_key',
        'last_augmented_spam_assets_detect_key',
    )
    movable_settings = write_cursor.execute(
        f'SELECT name, value FROM settings WHERE name IN ({",".join(["?"] * len(settings_moved))});',  # noqa: E501
        settings_moved,
    ).fetchall()
    write_cursor.executemany(
        'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?);',
        movable_settings,
    )
    write_cursor.execute(
        f'DELETE FROM settings WHERE name IN ({",".join(["?"] * len(movable_settings))});',
        [setting[0] for setting in movable_settings],
    )
    log.debug('Exit _move_non_settings_mappings_to_cache')


def maybe_move_value(write_cursor: 'DBCursor', pattern: str) -> None:
    """An auxiliary function to move `name` and `end_ts` from `used_query_ranges` table to
    `key_value_cache` table if it matches the given pattern"""
    rows = write_cursor.execute(
        'SELECT name, end_ts FROM used_query_ranges WHERE name LIKE ?',
        (pattern, ),
    ).fetchall()
    if len(rows) != 0:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?);', rows,
        )
        write_cursor.executemany(
            'DELETE FROM used_query_ranges WHERE name = ?', [(row[0],) for row in rows],
        )


def _upgrade_external_service_credentials(write_cursor: 'DBCursor') -> None:
    """Upgrade the external service credentials schema table to add a secret"""
    log.debug('Enter _upgrade_external_service_credentials')
    update_table_schema(
        write_cursor=write_cursor,
        table_name='external_service_credentials',
        schema="""name VARCHAR[30] NOT NULL PRIMARY KEY,
        api_key TEXT NOT NULL,
        api_secret TEXT""",
        insert_columns='name,api_key,null',
    )
    log.debug('Exit _upgrade_external_service_credentials')


def _move_non_intervals_from_used_query_ranges_to_cache(write_cursor: 'DBCursor') -> None:
    """Move timestamps that are not ranges from `used_query_ranges` to the `key_value_cache` table"""  # noqa: E501
    log.debug('Enter _move_non_intervals_from_used_query_ranges_to_cache')
    value_patterns = {
        '{pattern}%': (  # to match patterns with prefixes
            'ethwithdrawalsts_',
            'ethwithdrawalsidx_',
        ),
        '%{pattern}': (  # to match patterns with suffixes
            '_last_cryptotx_offset',
            '_last_query_ts',
            '_last_query_id',
        ),
        '{pattern}': (  # to match patterns as exact names
            'last_produced_blocks_query_ts',
            'last_withdrawals_exit_query_ts',
            'last_events_processing_task_ts',
        ),
    }
    for key, patterns in value_patterns.items():
        for pattern in patterns:
            maybe_move_value(write_cursor, key.format(pattern=pattern))
    log.debug('Exit _move_non_intervals_from_used_query_ranges_to_cache')


def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _add_new_supported_locations')
    write_cursor.execute(
        'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
        ('m', 45),
    )
    log.debug('Exit _add_new_supported_locations')


def _remove_covalent_api_key(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _remove_covalent_api_key')
    write_cursor.execute(
        'DELETE FROM external_service_credentials WHERE name=?',
        ('covalent', ),
    )
    log.debug('Exit _remove_covalent_api_key')


def _move_labels_to_addressbook(write_cursor: 'DBCursor') -> None:
    """Move all the `label` column values from `blockchain_accounts` table to the `name` column
    of the 'address_book` table. If a `name` already exists in the `address_book` table, then
    `address_name_priority` setting is used to determine which one to keep. Defaults to
    `DEFAULT_ADDRESS_NAME_PRIORITY`."""
    log.debug('Enter _move_labels_to_addressbook')
    address_name_priority = write_cursor.execute(  # get priority settings
        'SELECT value FROM settings WHERE name = "address_name_priority"',
    ).fetchone()
    if address_name_priority is not None:
        try:
            address_name_priority = json.loads(address_name_priority[0])
        except json.decoder.JSONDecodeError:
            log.error(
                'During v40->v41 DB upgrade a non-json address_name_priority setting was found: '
                f'{address_name_priority[0]}. Reverting to default.',
            )
            address_name_priority = DEFAULT_ADDRESS_NAME_PRIORITY
    else:
        address_name_priority = DEFAULT_ADDRESS_NAME_PRIORITY

    try:
        address_book_priority = address_name_priority.index('private_addressbook')
        blockchain_account_priority = address_name_priority.index('blockchain_account')
    except ValueError:
        address_book_priority, blockchain_account_priority = 0, 1
    labels_to_move = {  # get all the labels from `blockchain_accounts` table
        (account, blockchain): label for account, blockchain, label in write_cursor.execute(
            'SELECT account, blockchain, label FROM blockchain_accounts WHERE label IS NOT NULL',
        )
    }

    if address_book_priority < blockchain_account_priority:
        for address, blockchain in write_cursor.execute(
            'SELECT address, blockchain FROM address_book;',
        ):  # remove the labels_to_move that are already present in the address_book
            labels_to_move.pop((address, blockchain), None)

    write_cursor.executemany(  # insert all the prioritized labels into the `address_book` table
        'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES (?, ?, ?)',
        [(address, blockchain, name) for (address, blockchain), name in labels_to_move.items()],
    )
    # remove the `label` column from the `blockchain_accounts` table
    write_cursor.execute('ALTER TABLE blockchain_accounts DROP COLUMN label')
    log.debug('Exit _move_labels_to_addressbook')


def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
    """Reset all decoded evm events except the customized ones."""
    log.debug('Enter _reset_decoded_events')
    if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
        customized_events = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0]
        querystr = (
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN evm_events_info E '
            'ON H.identifier=E.identifier AND E.tx_hash IN '
            '(SELECT tx_hash FROM evm_transactions))'
        )
        bindings: tuple = ()
        if customized_events != 0:
            querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

        write_cursor.execute(querystr, bindings)
        write_cursor.execute(
            'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
            (HISTORY_MAPPING_STATE_DECODED,),
        )
    log.debug('Exit _reset_decoded_events')


def _remove_bittrex_data(write_cursor: 'DBCursor') -> None:
    """
    Removes bittrex settings and credentials from the DB.
    Code taken from v36->v37 upgrade from ftx.
    """
    log.debug('Enter _remove_bittrex_data')
    write_cursor.execute(
        'DELETE FROM user_credentials WHERE location=?',
        (Location.BITTREX.serialize_for_db(),),
    )
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
        (f'{Location.BITTREX!s}\\_%', '\\'),
    )
    non_syncing_exchanges_in_db = write_cursor.execute(
        'SELECT value FROM settings WHERE name="non_syncing_exchanges"',
    ).fetchone()
    if non_syncing_exchanges_in_db is not None:
        try:
            non_syncing_exchanges = json.loads(non_syncing_exchanges_in_db[0])
        except json.JSONDecodeError as e:
            log.error(
                f'Failed to read setting "non_syncing_exchanges" due to {e} '
                'during the DB upgrade to v41.',
            )
        else:
            new_values = [x for x in non_syncing_exchanges if x['location'] != Location.BITTREX.serialize()]  # noqa: E501
            write_cursor.execute(
                'UPDATE settings SET value=? WHERE name="non_syncing_exchanges"',
                (json.dumps(new_values),),
            )
    log.debug('Exit _remove_bittrex_data')


def upgrade_v40_to_v41(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v40 to v41. This was in v1.32 release.

        - Create a new table for key-value cache
        - Move non-settings and non-used query ranges to the new cache
        - Add new supported locations
        - remove any covalent api key added by the user
        - Move labels to `address_book` and drop its column from `blockchain_accounts`
    """
    log.debug('Enter userdb v40->v41 upgrade')
    progress_handler.set_total_steps(9)
    with db.user_write() as write_cursor:
        _add_cache_table(write_cursor)
        progress_handler.new_step()
        _remove_covalent_api_key(write_cursor)
        progress_handler.new_step()
        _remove_bittrex_data(write_cursor)
        progress_handler.new_step()
        _upgrade_external_service_credentials(write_cursor)
        progress_handler.new_step()
        _move_non_settings_mappings_to_cache(write_cursor)
        progress_handler.new_step()
        _move_non_intervals_from_used_query_ranges_to_cache(write_cursor)
        progress_handler.new_step()
        _add_new_supported_locations(write_cursor)
        progress_handler.new_step()
        _move_labels_to_addressbook(write_cursor)
        progress_handler.new_step()
        _reset_decoded_events(write_cursor)
    progress_handler.new_step()

    log.debug('Finish userdb v40->v41 upgrade')
