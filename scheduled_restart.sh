#!/bin/bash
# 定时重启守护进程
# 每天凌晨 2 点前后随机 0-30 分钟关闭，早上 7 点重启

SCRIPT="/root/TodayHIT/restart.sh"
LOG="/root/TodayHIT/restart.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [守护] $1" | tee -a "$LOG"
}

while true; do
    # 计算今天凌晨 2 点 + 随机 0-30 分钟
    HOUR=2
    RANDOM_MIN=$((RANDOM % 31))
    STOP_TIME=$(printf "%02d:%02d" $HOUR $RANDOM_MIN)

    # 计算今天早上 7 点
    START_HOUR=7
    START_MIN=$((RANDOM % 6))  # 7:00-7:05 随机
    START_TIME=$(printf "%02d:%02d" $START_HOUR $START_MIN)

    NOW_HOUR=$(date +%H)
    NOW_MIN=$(date +%M)

    log "下次关闭时间: 今天 $STOP_TIME，下次启动时间: 今天 $START_TIME"

    # 等到凌晨关闭时间
    while true; do
        CUR_HOUR=$(date +%H)
        CUR_MIN=$(date +%M)
        if [ "$CUR_HOUR" -ge 2 ] && [ "$CUR_HOUR" -lt 7 ]; then
            # 已过 2 点，检查是否到了停止时间
            if [ "$CUR_HOUR" -gt "$HOUR" ] || ([ "$CUR_HOUR" -eq "$HOUR" ] && [ "$CUR_MIN" -ge "$RANDOM_MIN" ]); then
                log "到达关闭时间，开始关闭..."
                bash "$SCRIPT" stop
                break
            fi
        fi
        # 如果已经过了 7 点但还没停，跳过今天
        if [ "$CUR_HOUR" -ge 7 ]; then
            log "已过 7 点，跳过今天的关闭"
            break
        fi
        sleep 30
    done

    # 等到早上 7 点启动
    while true; do
        CUR_HOUR=$(date +%H)
        CUR_MIN=$(date +%M)
        if [ "$CUR_HOUR" -ge 7 ] && [ "$CUR_HOUR" -lt 2 ]; then
            break  # 不应该到这里
        fi
        if [ "$CUR_HOUR" -ge 7 ]; then
            if [ "$CUR_HOUR" -gt "$START_HOUR" ] || ([ "$CUR_HOUR" -eq "$START_HOUR" ] && [ "$CUR_MIN" -ge "$START_MIN" ]); then
                log "到达启动时间，开始启动..."
                bash "$SCRIPT" start
                break
            fi
        fi
        sleep 30
    done

    # 启动后等到下一个循环（第二天凌晨 2 点前）
    log "今日重启完成，等待明天..."
    sleep 3600  # 每小时检查一次，防止错过
done
