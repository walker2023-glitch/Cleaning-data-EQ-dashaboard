"""Centralized help coverage and business caveats; no GUI or networking required."""
from equipment_data_manager.ui.help_content import HELP, missing_help


def test_required_control_registry_is_complete_and_maintainable():
    required={'discover','preview','process','packet','correction','powerbi','legacy','history','load_config','month',
        'raw_folder','candidate_folder','approved_folder','repairs','service_orders','tma_work_orders','warnings'}
    assert required <= HELP.keys()
    for key,entry in HELP.items():
        assert entry.control_id==key and entry.title and entry.brief and entry.detailed
        assert entry.dashboard and entry.affects and entry.next_step and entry.guide
        assert len(entry.text('detailed')) > len(entry.text('brief'))
        assert 'SYNTHETIC CONTEXT' in entry.text('brief','SYNTHETIC CONTEXT')
        assert 'SYNTHETIC CONTEXT' in entry.text('detailed','SYNTHETIC CONTEXT')


def test_source_explanations_preserve_financial_and_unsupported_format_limits():
    assert 'business validation' in HELP['repairs'].text()
    assert 'not an implemented feature' in HELP['service_orders'].text()
    assert 'Tim' in HELP['tma_work_orders'].text() and 'Do not rename' in HELP['tma_work_orders'].text()
    assert 'not an approved production release' in HELP['packet'].text()
    assert 'does not provide business or financial approval' in HELP['correction'].text()
    assert 'Do not ignore' in HELP['warnings'].text()


def test_missing_reports_explain_which_export_to_obtain():
    text=missing_help({'repairs','service_orders','tma_work_orders'})
    assert 'Repair Report' in text and 'Service Orders List' in text and 'CSV' in text
    assert 'Tim' in text and 'XLSX' in text
    assert not missing_help(set())


def test_scaled_window_sizes_leave_room_for_taskbar():
    from equipment_data_manager.ui.app import window_size
    assert window_size(1600,1000,1)==(1280,920)
    assert window_size(1920,1080,1.5)==(1240,656)
    assert window_size(1920,1080,2)==(920,476)


def test_bundled_employee_guide_matches_maintained_document():
    from importlib.resources import files
    from pathlib import Path
    bundled=files('equipment_data_manager').joinpath('resources','guides','user_guide.md').read_text(encoding='utf-8')
    maintained=(Path(__file__).parents[1] / 'docs/user_guide.md').read_text(encoding='utf-8')
    assert bundled==maintained
    assert 'First launch: Settings' in bundled and 'Guided Mode and keyboard help' in bundled
