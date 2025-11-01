"""Unit tests for the test command helper functions."""

import pytest

from saitest.cli.main import (
    calculate_match_confidence,
    compare_lists,
    compare_saidata_details
)


class TestCompareListsFunction:
    """Tests for the compare_lists helper function."""
    
    def test_identical_lists(self):
        """Test that identical lists return 1.0 score."""
        list1 = ['a', 'b', 'c']
        list2 = ['a', 'b', 'c']
        assert compare_lists(list1, list2) == 1.0
    
    def test_completely_different_lists(self):
        """Test that completely different lists return 0.0 score."""
        list1 = ['a', 'b', 'c']
        list2 = ['d', 'e', 'f']
        assert compare_lists(list1, list2) == 0.0
    
    def test_partial_overlap(self):
        """Test that partially overlapping lists return correct score."""
        list1 = ['a', 'b', 'c']
        list2 = ['b', 'c', 'd']
        # Intersection: {b, c} = 2, Union: {a, b, c, d} = 4
        # Score: 2/4 = 0.5
        assert compare_lists(list1, list2) == 0.5
    
    def test_empty_lists(self):
        """Test that two empty lists return 1.0 score."""
        assert compare_lists([], []) == 1.0
    
    def test_one_empty_list(self):
        """Test that one empty list returns 0.0 score."""
        assert compare_lists(['a', 'b'], []) == 0.0
        assert compare_lists([], ['a', 'b']) == 0.0
    
    def test_lists_with_none_values(self):
        """Test that None values are filtered out."""
        list1 = ['a', None, 'b']
        list2 = ['a', 'b', None]
        assert compare_lists(list1, list2) == 1.0


class TestCalculateMatchConfidence:
    """Tests for the calculate_match_confidence function."""
    
    def test_identical_saidata(self):
        """Test that identical saidata returns high confidence."""
        saidata = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}],
            'files': [{'path': '/usr/bin/nginx'}],
            'commands': [{'name': 'nginx'}],
            'ports': [{'number': 80}]
        }
        score = calculate_match_confidence(saidata, saidata)
        assert score == 1.0
    
    def test_completely_different_saidata(self):
        """Test that completely different saidata returns low confidence."""
        existing = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}]
        }
        generated = {
            'packages': [{'name': 'apache', 'package_name': 'apache2'}],
            'services': [{'name': 'apache2'}]
        }
        score = calculate_match_confidence(existing, generated)
        assert score == 0.0
    
    def test_partial_match(self):
        """Test that partially matching saidata returns intermediate confidence."""
        existing = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}, {'name': 'nginx-debug'}]
        }
        generated = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}]
        }
        score = calculate_match_confidence(existing, generated)
        # Packages: 1.0 (perfect match - nginx in both)
        # Services: 0.5 (1/2 match - nginx in both, nginx-debug only in existing)
        # Average: (1.0 + 0.5) / 2 = 0.75
        assert score == 0.75
    
    def test_with_overrides_structure(self):
        """Test that generated saidata with overrides structure is handled correctly."""
        existing = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}]
        }
        generated = {
            'default': {
                'packages': [{'name': 'nginx', 'package_name': 'nginx'}]
            },
            'overrides': {
                'ubuntu': {'22.04': {}}
            }
        }
        score = calculate_match_confidence(existing, generated)
        assert score == 1.0
    
    def test_empty_saidata(self):
        """Test that empty saidata returns 0.0 confidence."""
        score = calculate_match_confidence({}, {})
        assert score == 0.0


class TestCompareSaidataDetails:
    """Tests for the compare_saidata_details function."""
    
    def test_detailed_comparison(self):
        """Test that detailed comparison returns correct format."""
        existing = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}],
            'files': [{'path': '/usr/bin/nginx'}],
            'commands': [{'name': 'nginx'}],
            'ports': [{'number': 80}]
        }
        generated = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}],
            'services': [{'name': 'nginx'}],
            'files': [{'path': '/usr/bin/nginx'}, {'path': '/etc/nginx/nginx.conf'}],
            'commands': [{'name': 'nginx'}],
            'ports': [{'number': 80}, {'number': 443}]
        }
        
        details = compare_saidata_details(existing, generated)
        
        assert 'Packages' in details
        assert 'Services' in details
        assert 'Files' in details
        assert 'Commands' in details
        assert 'Ports' in details
        
        # Packages: 1/1 match
        assert details['Packages'] == '1/1 match'
        # Services: 1/1 match
        assert details['Services'] == '1/1 match'
        # Files: 1/2 match (nginx binary in both, nginx.conf only in generated)
        assert details['Files'] == '1/2 match'
        # Commands: 1/1 match
        assert details['Commands'] == '1/1 match'
        # Ports: 1/2 match (80 in both, 443 only in generated)
        assert details['Ports'] == '1/2 match'
    
    def test_with_overrides_structure(self):
        """Test that overrides structure is handled correctly."""
        existing = {
            'packages': [{'name': 'nginx', 'package_name': 'nginx'}]
        }
        generated = {
            'default': {
                'packages': [{'name': 'nginx', 'package_name': 'nginx'}]
            }
        }
        
        details = compare_saidata_details(existing, generated)
        assert details['Packages'] == '1/1 match'
