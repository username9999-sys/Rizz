#!/bin/bash
# Rizz Platform - Automated Backup Script
# Usage: ./backup.sh [full|incremental] [destination]

set -e

# Configuration
BACKUP_TYPE=${1:-full}
BACKUP_DEST=${2:-/backups}
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/rizz_backup_${DATE}.log"
RETENTION_DAYS=7

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a $LOG_FILE
}

# Create backup directory
mkdir -p ${BACKUP_DEST}

log "Starting ${BACKUP_TYPE} backup..."
log "Backup destination: ${BACKUP_DEST}"

# Backup PostgreSQL
backup_postgres() {
    log "Backing up PostgreSQL databases..."
    
    for db in rizz rizz_api rizz_ecommerce; do
        pg_dump -U postgres -h localhost ${db} > ${BACKUP_DEST}/postgres_${db}_${DATE}.sql 2>> $LOG_FILE
        gzip ${BACKUP_DEST}/postgres_${db}_${DATE}.sql
        log "  ✓ ${db} backed up"
    done
}

# Backup MongoDB
backup_mongodb() {
    log "Backing up MongoDB databases..."
    
    mongodump --host localhost --db rizz_streaming --out ${BACKUP_DEST}/mongo_${DATE} 2>> $LOG_FILE
    mongodump --host localhost --db rizz_social --out ${BACKUP_DEST}/mongo_${DATE} 2>> $LOG_FILE
    mongodump --host localhost --db rizz_cloud --out ${BACKUP_DEST}/mongo_${DATE} 2>> $LOG_FILE
    
    tar -czf ${BACKUP_DEST}/mongo_${DATE}.tar.gz ${BACKUP_DEST}/mongo_${DATE}
    rm -rf ${BACKUP_DEST}/mongo_${DATE}
    
    log "  ✓ MongoDB databases backed up"
}

# Backup Redis
backup_redis() {
    log "Backing up Redis..."
    
    redis-cli SAVE
    cp /var/lib/redis/dump.rdb ${BACKUP_DEST}/redis_${DATE}.rdb
    gzip ${BACKUP_DEST}/redis_${DATE}.rdb
    
    log "  ✓ Redis backed up"
}

# Backup Elasticsearch
backup_elasticsearch() {
    log "Backing up Elasticsearch indices..."
    
    curl -X POST "localhost:9200/_snapshot/rizz_backup/snapshot_${DATE}" \
        -H 'Content-Type: application/json' \
        -d '{
            "indices": "rizz_*",
            "ignore_unavailable": true,
            "include_global_state": false
        }' 2>> $LOG_FILE
    
    log "  ✓ Elasticsearch indices snapshot created"
}

# Backup application files
backup_files() {
    log "Backing up application files..."
    
    # Important directories
    dirs=(
        "/data/data/com.termux/files/home/Rizz-Project"
        "/etc/nginx/nginx.conf"
        "/etc/letsencrypt"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            tar -czf ${BACKUP_DEST}/files_$(basename $dir)_${DATE}.tar.gz $dir 2>> $LOG_FILE
            log "  ✓ ${dir} backed up"
        fi
    done
}

# Backup Docker volumes
backup_volumes() {
    log "Backing up Docker volumes..."
    
    volumes=$(docker volume ls -q | grep rizz)
    
    for volume in $volumes; do
        docker run --rm \
            -v ${volume}:/volume:ro \
            -v ${BACKUP_DEST}:/backup \
            alpine \
            tar -czf /backup/volume_${volume}_${DATE}.tar.gz /volume 2>> $LOG_FILE
        
        log "  ✓ Volume ${volume} backed up"
    done
}

# Upload to cloud storage
upload_to_cloud() {
    log "Uploading backups to cloud storage..."
    
    # AWS S3
    if command -v aws &> /dev/null; then
        aws s3 cp ${BACKUP_DEST}/ s3://rizz-backups/${DATE}/ --recursive 2>> $LOG_FILE
        log "  ✓ Uploaded to AWS S3"
    fi
    
    # Google Cloud Storage
    if command -v gsutil &> /dev/null; then
        gsutil -m cp -r ${BACKUP_DEST}/* gs://rizz-backups/${DATE}/ 2>> $LOG_FILE
        log "  ✓ Uploaded to Google Cloud Storage"
    fi
}

# Cleanup old backups
cleanup() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    find ${BACKUP_DEST} -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    find ${BACKUP_DEST} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    find ${BACKUP_DEST} -name "*.rdb.gz" -mtime +${RETENTION_DAYS} -delete
    
    log "  ✓ Cleanup completed"
}

# Main backup function
run_backup() {
    case ${BACKUP_TYPE} in
        full)
            backup_postgres
            backup_mongodb
            backup_redis
            backup_elasticsearch
            backup_files
            backup_volumes
            upload_to_cloud
            ;;
        incremental)
            backup_postgres
            backup_redis
            backup_volumes
            ;;
        *)
            error "Unknown backup type: ${BACKUP_TYPE}"
            exit 1
            ;;
    esac
}

# Execute backup
run_backup

# Cleanup
cleanup

# Generate backup report
generate_report() {
    log "Generating backup report..."
    
    REPORT_FILE=${BACKUP_DEST}/backup_report_${DATE}.txt
    
    {
        echo "Rizz Platform Backup Report"
        echo "=========================="
        echo "Date: $(date)"
        echo "Type: ${BACKUP_TYPE}"
        echo ""
        echo "Backup Files:"
        ls -lh ${BACKUP_DEST}/*${DATE}* 2>/dev/null
        echo ""
        echo "Total Size:"
        du -sh ${BACKUP_DEST} 2>/dev/null
    } > ${REPORT_FILE}
    
    log "  ✓ Report generated: ${REPORT_FILE}"
}

generate_report

log "Backup completed successfully!"
log "Log file: ${LOG_FILE}"

# Send notification (optional)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ Rizz Platform Backup Completed (${BACKUP_TYPE})\"}" \
        $SLACK_WEBHOOK_URL
fi

exit 0
