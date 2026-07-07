/**
 * Новые возможности PropertyInspector 2.5.0 =>
 * 
 *1=> Инструмент отделен от основного файла - вводится по запросу
 *2 => $settings - глобальный постоянный прокси-сервер данных ※
 *3=> Не нужно обращать внимание на контекст - общайтесь с плагинами в любое время и в любом месте.
 *4=> Меры предосторожности: Во избежание конфликтов имен, пожалуйста, не используйте связанные с $ имена и библиотеку jQuery
 * 
 * ===== Мирабокс ========================================== 2025.4.9 =====>
 */

let $websocket, $uuid, $action, $context, $settings, $lang;

// 设置全局持久化数据
WebSocket.prototype.setGlobalSettings = function(payload) {
    this.send(JSON.stringify({
        event: "setGlobalSettings",
        context: $uuid, payload
    }));
}

// 获取全局持久化数据
WebSocket.prototype.getGlobalSettings = function() {
    this.send(JSON.stringify({
        event: "getGlobalSettings",
        context: $uuid,
    }));
}

// 与插件通信
WebSocket.prototype.sendToPlugin = function (payload) {
    this.send(JSON.stringify({
        event: "sendToPlugin",
        action: $action,
        context: $uuid,
        payload
    }));
}

// 设置状态
WebSocket.prototype.setState = function (state) {
    this.send(JSON.stringify({
        event: "setState",
        context: $context,
        payload: { state }
    }));
}

// 设置背景
WebSocket.prototype.setImage = function (url) {
    let image = new Image();
    image.src = url;
    image.onload = () => {
        let canvas = document.createElement("canvas");
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        let ctx = canvas.getContext("2d");
        ctx.drawImage(image, 0, 0);
        this.send(JSON.stringify({
            event: "setImage",
            context: $context,
            payload: {
                target: 0,
                image: canvas.toDataURL("image/png")
            }
        }));
    };
}

// 打开网页
WebSocket.prototype.openUrl = function (url) {
    this.send(JSON.stringify({
        event: "openUrl",
        payload: { url }
    }));
}

// 保存持久化数据
WebSocket.prototype.saveData = $.debounce(function (payload) {
    this.send(JSON.stringify({
        event: "setSettings",
        context: $uuid,
        payload
    }))
}, 0)

// Функция ввода программного обеспечения StreamDock
const connectSocket = connectElgatoStreamDeckSocket;
async function connectElgatoStreamDeckSocket(port, uuid, event, app, info) {
    info = JSON.parse(info);
    $uuid = uuid; $action = info.action; $context = info.context;
    $websocket = new WebSocket('ws://127.0.0.1:' + port);
    $websocket.onopen = () => $websocket.send(JSON.stringify({ event, uuid }));

    // Постоянный прокси-сервер передачи данных
    $websocket.onmessage = e => {
        let data = JSON.parse(e.data);
        if (data.event === 'didReceiveSettings') {
            $settings = new Proxy(data.payload.settings, {
                get(target, property) {
                    return target[property];
                },
                set(target, property, value) {
                    target[property] = value;
                    $websocket.saveData(data.payload.settings);
                }
            });
            if (!$back) $dom.main.style.display = 'block';
        }
        $propEvent[data.event]?.(data.payload);
    };

    // Автоматический перевод страниц
    if (!$local) return;
    $lang = await new Promise(resolve => {
        const req = new XMLHttpRequest();
        req.open('GET', `../../${JSON.parse(app).application.language}.json`);
        req.send();
        req.onreadystatechange = () => {
            if (req.readyState === 4) {
                // console.log(req.responseText);
                resolve(JSON.parse(req.responseText).Localization)
            }
        };
    })

    // Обход текстовых узлов и перевод всех текстовых узлов
    const walker = document.createTreeWalker($dom.main, NodeFilter.SHOW_TEXT, (e) => {
        return e.data.trim() && NodeFilter.FILTER_ACCEPT
    });
    while (walker.nextNode()) {
        console.log(walker.currentNode.data);
        walker.currentNode.data = $lang[walker.currentNode.data]
    }
    // placeholder 特殊处理
    const translate = item => {
        if (item.placeholder?.trim()) {
            console.log(item.placeholder);
            item.placeholder = $lang[item.placeholder]
        }
    }
    $('input', true).forEach(translate)
    $('textarea', true).forEach(translate)
}

// Обратный вызов пути к файлу StreamDock
let $FileID = ''; Array.from($('input[type="file"]', true)).forEach(item => {
    item.addEventListener('click', () => $FileID = item.id);
});
const onFilePickerReturn = (url) => $emit.send(`File-${$FileID}`, JSON.parse(url));