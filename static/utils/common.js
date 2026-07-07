// Пользовательский класс событий
class EventPlus {
    constructor() {
        this.event = new EventTarget();
    }
    on(name, callback) {
        this.event.addEventListener(name, e => callback(e.detail));
    }
    send(name, data) {
        this.event.dispatchEvent(new CustomEvent(name, {
            detail: data,
            bubbles: false,
            cancelable: false
        }));
    }
}

// Свести к нулю
String.prototype.fill = function () {
    return this >= 10 ? this : '0' + this
}

// строка преобразования кодировки в юникод
String.prototype.uTs = function () {
    return eval('"' + Array.from(this).join('') + '"');
};

// Преобразование строк в кодировку unicode
String.prototype.sTu = function (str = '') {
    Array.from(this).forEach(item => str += `\\u${item.charCodeAt(0).toString(16)}`);
    return str;
};

// Глобальные переменные/методы
const $emit = new EventPlus(), $ = (selector, isAll = false) => {
    const element = document.querySelector(selector);
    const methods = {
        on: function (event, callback) {
            this.addEventListener(event, callback)
        },
        attr: function (name, value = '') {
            value && this.setAttribute(name, value);
            return this;
        }
    }
    if (!isAll && element) {
        return Object.assign(element, methods)
    } else if (!isAll && !element) {
        throw `В HTML нет элемента ${selector}! Пожалуйста, проверьте, нет ли орфографических ошибок`
    }
    return Array.from(document.querySelectorAll(selector)).map(item => Object.assign(item, methods))
}

// Функция регулирования
$.throttle = (fn, delay) => {
    let Timer = null;
    return function () {
        if (Timer) return;
        Timer = setTimeout(() => {
            fn.apply(this, arguments);
            Timer = null;
        }, delay);
    };
};

// 防抖函数
$.debounce = (fn, delay) => {
    let Timer = null;
    return function () {
        clearTimeout(Timer);
        Timer = setTimeout(() => fn.apply(this, arguments), delay);
    };
};

// Предельное количество
$.num = (selector) => {
    if (!selector.value || /^\d+$/.test(selector.value)) return;
    selector.value = selector.value.slice(0, -1);
    $.num(selector);
};

// Способ определения номера ограничения привязки
Array.from($('input[type="num"]', true)).forEach(item => {
    item.addEventListener('input', () => $.num(item));
});