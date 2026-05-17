#!/bin/bash
# TodayHIT 自动重启脚本
# 凌晨 2 点前后随机关闭，早上 7 点重新启动

LOG="/root/TodayHIT/restart.log"
PYTHON="/root/TodayHIT/venv/bin/python"
BOT_QQ="3943456425"
WS_URL="ws://127.0.0.1:8080/onebot/v11/ws"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

configure_napcat_ws() {
    # 写入 WebSocket 配置到容器
    local TMPJSON="/tmp/onebot11_${BOT_QQ}.json"
    cat > "$TMPJSON" << EOF
{
  "websocketClients": [
    "${WS_URL}"
  ]
}
EOF
    podman cp "$TMPJSON" "napcat:/app/napcat/config/onebot11_${BOT_QQ}.json" 2>/dev/null
    rm -f "$TMPJSON"
    log "WebSocket 配置已写入"
}

stop_all() {
    log "停止 Bot..."
    pkill -f "python bot.py" 2>/dev/null
    sleep 2

    log "停止 NapCat 容器..."
    podman stop napcat 2>/dev/null
    sleep 2

    log "清理残留进程..."
    pkill -f "napcat" 2>/dev/null

    log "全部停止完成"
}

start_all() {
    log "启动 NapCat 容器..."
    podman start napcat 2>/dev/null || {
        log "容器不存在，重新创建..."
        podman run -d --name napcat --network=host \
            docker.m.daocloud.io/mlikiowa/napcat-docker:latest
    }

    # 写入 WebSocket 配置
    sleep 3
    configure_napcat_ws

    log "等待 NapCat 启动并登录（60 秒）..."
    sleep 60

    # 检查 NapCat 是否在运行
    if podman ps | grep -q napcat; then
        log "NapCat 运行正常"
    else
        log "NapCat 未运行，尝试重启..."
        podman restart napcat
        sleep 30
    fi

    log "启动 Bot..."
    cd /root/TodayHIT
    nohup "$PYTHON" bot.py >> "$LOG" 2>&1 &
    BOT_PID=$!
    log "Bot 已启动 (PID: $BOT_PID)"

    # 等待 Bot 连接
    sleep 10
    if ps -p $BOT_PID > /dev/null 2>&1; then
        log "Bot 进程运行正常"
    else
        log "Bot 启动失败，重试一次..."
        nohup "$PYTHON" bot.py >> "$LOG" 2>&1 &
        log "Bot 重试启动 (PID: $!)"
    fi
}

# ── 主逻辑 ──

case "$1" in
    stop)
        stop_all
        ;;
    start)
        start_all
        ;;
    restart)
        stop_all
        sleep 5
        start_all
        ;;
    *)
        echo "用法: $0 {stop|start|restart}"
        exit 1
        ;;
esac
