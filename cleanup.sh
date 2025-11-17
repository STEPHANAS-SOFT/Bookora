#!/bin/bash
###############################################################################
# Bookora Backend - Log and Temporary File Cleanup Script
#
# This script performs cleanup of old logs, temporary files, and cached data
# to maintain system performance and manage disk space.
#
# Usage:
#   ./cleanup.sh [options]
#
# Options:
#   --logs              Clean old log files
#   --cache             Clean cache files
#   --temp              Clean temporary files
#   --all               Clean everything (default)
#   --dry-run           Show what would be deleted
#   --force             Skip confirmations
#   --help              Show this help message
#
# Cron Setup (weekly cleanup on Sunday at 3 AM):
#   0 3 * * 0 /path/to/cleanup.sh --all >> /path/to/logs/cleanup.log 2>&1
#
# Author: Bookora Team
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="${SCRIPT_DIR}/logs"
CACHE_DIR="${SCRIPT_DIR}/__pycache__"
TEMP_DIR="${SCRIPT_DIR}/tmp"
BACKUP_DIR="${SCRIPT_DIR}/backups"

# Options
CLEAN_LOGS=false
CLEAN_CACHE=false
CLEAN_TEMP=false
DRY_RUN=false
FORCE=false

# Retention periods (in days)
LOG_RETENTION=30
BACKUP_RETENTION=90
TEMP_RETENTION=7

###############################################################################
# Helper Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║          🧹 CLEANUP AUTOMATION SYSTEM 🧹                 ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    local message="$1"
    read -p "$(echo -e ${YELLOW}"$message (y/N): "${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipped"
        return 1
    fi
    return 0
}

get_size() {
    if [ -d "$1" ]; then
        du -sh "$1" 2>/dev/null | cut -f1 || echo "0K"
    else
        echo "0K"
    fi
}

###############################################################################
# Parse Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --logs)
            CLEAN_LOGS=true
            shift
            ;;
        --cache)
            CLEAN_CACHE=true
            shift
            ;;
        --temp)
            CLEAN_TEMP=true
            shift
            ;;
        --all)
            CLEAN_LOGS=true
            CLEAN_CACHE=true
            CLEAN_TEMP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: ./cleanup.sh [options]"
            echo ""
            echo "Options:"
            echo "  --logs              Clean old log files"
            echo "  --cache             Clean cache files"
            echo "  --temp              Clean temporary files"
            echo "  --all               Clean everything"
            echo "  --dry-run           Show what would be deleted"
            echo "  --force             Skip confirmations"
            echo "  --help              Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to cleaning all if nothing specified
if [ "$CLEAN_LOGS" = false ] && [ "$CLEAN_CACHE" = false ] && [ "$CLEAN_TEMP" = false ]; then
    CLEAN_LOGS=true
    CLEAN_CACHE=true
    CLEAN_TEMP=true
fi

###############################################################################
# Cleanup Functions
###############################################################################

cleanup_old_logs() {
    print_section "Cleaning Old Log Files"
    
    if [ ! -d "$LOGS_DIR" ]; then
        print_info "Logs directory not found"
        return 0
    fi
    
    local before_size=$(get_size "$LOGS_DIR")
    print_info "Current logs size: $before_size"
    
    # Find old log files
    local old_logs=$(find "$LOGS_DIR" -name "*.log" -type f -mtime "+$LOG_RETENTION" 2>/dev/null)
    
    if [ -z "$old_logs" ]; then
        print_info "No old log files to clean"
        return 0
    fi
    
    local count=$(echo "$old_logs" | wc -l | xargs)
    print_warning "Found $count log file(s) older than $LOG_RETENTION days"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Dry run - files that would be deleted:${NC}"
        echo "$old_logs" | while read -r file; do
            echo "  - $(basename "$file")"
        done
        return 0
    fi
    
    if ! confirm "Delete these log files?"; then
        return 0
    fi
    
    # Delete old logs
    echo "$old_logs" | while read -r file; do
        rm -f "$file"
        print_info "Deleted: $(basename "$file")"
    done
    
    # Compress recent logs
    print_info "Compressing recent log files..."
    find "$LOGS_DIR" -name "*.log" -type f -mtime "+7" -mtime "-$LOG_RETENTION" -exec gzip {} \; 2>/dev/null || true
    
    local after_size=$(get_size "$LOGS_DIR")
    print_success "Logs cleaned. New size: $after_size"
}

cleanup_cache() {
    print_section "Cleaning Cache Files"
    
    local deleted_count=0
    local before_size=0
    
    # Find all __pycache__ directories
    local cache_dirs=$(find "$SCRIPT_DIR" -type d -name "__pycache__" 2>/dev/null)
    
    if [ -z "$cache_dirs" ]; then
        print_info "No cache directories found"
        return 0
    fi
    
    # Calculate total size
    while IFS= read -r dir; do
        local size=$(du -sk "$dir" 2>/dev/null | cut -f1 || echo "0")
        before_size=$((before_size + size))
    done <<< "$cache_dirs"
    
    local count=$(echo "$cache_dirs" | wc -l | xargs)
    print_warning "Found $count cache director(ies) (${before_size}KB total)"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Dry run - directories that would be deleted:${NC}"
        echo "$cache_dirs" | while read -r dir; do
            echo "  - $dir"
        done
        return 0
    fi
    
    if ! confirm "Delete cache directories?"; then
        return 0
    fi
    
    # Delete cache directories
    while IFS= read -r dir; do
        rm -rf "$dir"
        ((deleted_count++))
    done <<< "$cache_dirs"
    
    # Also clean .pyc files
    find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
    
    print_success "Deleted $deleted_count cache director(ies)"
}

cleanup_temp_files() {
    print_section "Cleaning Temporary Files"
    
    if [ ! -d "$TEMP_DIR" ]; then
        print_info "Temp directory not found"
        return 0
    fi
    
    local before_size=$(get_size "$TEMP_DIR")
    print_info "Current temp size: $before_size"
    
    # Find old temp files
    local old_temps=$(find "$TEMP_DIR" -type f -mtime "+$TEMP_RETENTION" 2>/dev/null)
    
    if [ -z "$old_temps" ]; then
        print_info "No old temp files to clean"
        return 0
    fi
    
    local count=$(echo "$old_temps" | wc -l | xargs)
    print_warning "Found $count temp file(s) older than $TEMP_RETENTION days"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Dry run - files that would be deleted:${NC}"
        echo "$old_temps" | head -n 20 | while read -r file; do
            echo "  - $(basename "$file")"
        done
        if [ $count -gt 20 ]; then
            echo "  ... and $((count - 20)) more"
        fi
        return 0
    fi
    
    if ! confirm "Delete these temp files?"; then
        return 0
    fi
    
    # Delete old temp files
    echo "$old_temps" | while read -r file; do
        rm -f "$file"
    done
    
    local after_size=$(get_size "$TEMP_DIR")
    print_success "Temp files cleaned. New size: $after_size"
}

cleanup_old_backups() {
    print_section "Cleaning Old Backups"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_info "Backup directory not found"
        return 0
    fi
    
    local before_size=$(get_size "$BACKUP_DIR")
    print_info "Current backups size: $before_size"
    
    # Find old backup files
    local old_backups=$(find "$BACKUP_DIR" -name "*.sql*" -type f -mtime "+$BACKUP_RETENTION" 2>/dev/null)
    
    if [ -z "$old_backups" ]; then
        print_info "No old backups to clean (retention: $BACKUP_RETENTION days)"
        return 0
    fi
    
    local count=$(echo "$old_backups" | wc -l | xargs)
    print_warning "Found $count backup file(s) older than $BACKUP_RETENTION days"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Dry run - files that would be deleted:${NC}"
        echo "$old_backups" | while read -r file; do
            echo "  - $(basename "$file")"
        done
        return 0
    fi
    
    if ! confirm "Delete these old backups?"; then
        return 0
    fi
    
    # Delete old backups and their checksums
    echo "$old_backups" | while read -r file; do
        rm -f "$file"
        rm -f "${file}.sha256"
        print_info "Deleted: $(basename "$file")"
    done
    
    local after_size=$(get_size "$BACKUP_DIR")
    print_success "Old backups cleaned. New size: $after_size"
}

cleanup_docker() {
    print_section "Cleaning Docker Resources"
    
    if ! command -v docker &> /dev/null; then
        print_info "Docker not installed, skipping"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run - Docker cleanup would be performed"
        return 0
    fi
    
    if ! confirm "Clean unused Docker resources?"; then
        return 0
    fi
    
    print_info "Removing unused Docker images..."
    docker image prune -f || true
    
    print_info "Removing unused Docker containers..."
    docker container prune -f || true
    
    print_info "Removing unused Docker volumes..."
    docker volume prune -f || true
    
    print_info "Removing unused Docker networks..."
    docker network prune -f || true
    
    print_success "Docker resources cleaned"
}

print_summary() {
    print_section "Cleanup Summary"
    
    echo -e "${GREEN}✅ Cleanup completed!${NC}\n"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}This was a dry run. No files were actually deleted.${NC}"
        echo -e "${YELLOW}Run without --dry-run to perform actual cleanup.${NC}\n"
    fi
    
    echo -e "${CYAN}💾 Current Disk Usage:${NC}"
    if [ -d "$LOGS_DIR" ]; then
        echo -e "   Logs: $(get_size "$LOGS_DIR")"
    fi
    if [ -d "$BACKUP_DIR" ]; then
        echo -e "   Backups: $(get_size "$BACKUP_DIR")"
    fi
    if [ -d "$TEMP_DIR" ]; then
        echo -e "   Temp: $(get_size "$TEMP_DIR")"
    fi
    
    echo -e "\n${CYAN}💡 Recommendations:${NC}"
    echo -e "   • Set up automated cleanup: add to crontab"
    echo -e "   • Monitor disk usage: df -h"
    echo -e "   • Configure log rotation: see logrotate.conf"
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_banner
    
    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN MODE - No files will be deleted"
    fi
    
    # Run cleanup operations
    if [ "$CLEAN_LOGS" = true ]; then
        cleanup_old_logs
    fi
    
    if [ "$CLEAN_CACHE" = true ]; then
        cleanup_cache
    fi
    
    if [ "$CLEAN_TEMP" = true ]; then
        cleanup_temp_files
    fi
    
    # Always clean old backups when cleaning logs
    if [ "$CLEAN_LOGS" = true ]; then
        cleanup_old_backups
    fi
    
    # Optional: Docker cleanup
    # cleanup_docker
    
    # Print summary
    print_summary
}

# Trap signals
trap 'echo -e "\n${YELLOW}⏸️  Cleanup interrupted${NC}"; exit 130' INT

# Run main
main

exit 0

