/**
 * Описание основных параметров:
 * @local - интернационализированным
 * @back Самостоятельно определяет время отправки эхо-сигнала
 *@dom сохраняет необходимые элементы документа
 * Режим стратегии обратного вызова программного обеспечения @propEvent
 * ==================================================>
 */
const $local = true, $back = false,
    $dom = {
        main: $('.sdpi-wrapper'),
        emoteCountSelect: $('#emote_count_select'),
        rangeContainer: $('#range_settings_container'),
        minRange: $('#min_range'),
        maxRange: $('#max_range'),
        minTitle: $('#min_title'),
        maxTitle: $('#max_title')
    },
    $propEvent = {
        // Вызывается автоматически, когда PI открывается и получает текущие настройки из Stream Dock
        didReceiveSettings(data) {
            console.log("didReceiveSettings", data);
            $settings.test = 121;
            $websocket.sendToPlugin({ PropertyInspector: 121 });
            $websocket.setGlobalSettings({ PropertyInspector: 165415 });
            
            let minVal = 1, maxVal = 1;
            if ($settings) {
                if ($settings.emote_count !== undefined) {
                    $dom.emoteCountSelect.value = $settings.emote_count;
                }
                minVal = ($settings.min_emotes !== undefined) ? $settings.min_emotes : 1;
                maxVal = ($settings.max_emotes !== undefined) ? $settings.max_emotes : 5;
            }


            // Устанавливаем начальные нативные ограничения
            $dom.minRange.max = maxVal;
            $dom.maxRange.min = minVal;

            $dom.minRange.value = minVal;
            $dom.maxRange.value = maxVal;

            $dom.minTitle.textContent = `Минимум: ${minVal}`;
            $dom.maxTitle.textContent = `Максимум: ${maxVal}`;
            
            toggleRangeContainer($dom.emoteCountSelect.value)
        },
        sendToPropertyInspector(data) {
            console.log("sendToPropertyInspector", data);
        },
        didReceiveGlobalSettings(data) {
            console.log("didReceiveGlobalSettings", data);
        },
    };

function toggleRangeContainer(value) {
    if (value === 'random') {
        $dom.rangeContainer.classList.remove('hidden');
    } else {
        $dom.rangeContainer.classList.add('hidden');
    }
}

// Следим за изменением значения в списке пользователем
$dom.emoteCountSelect.on('change', () => {
    const value = $dom.emoteCountSelect.value;

    if (value === 'random') {
        $settings.emote_count = 'random';

        if ($settings.min_emotes === undefined) $settings.min_emotes = parseInt($dom.minRange.value);
        if ($settings.max_emotes === undefined) $settings.max_emotes = parseInt($dom.maxRange.value);
    } else {
        $settings.emote_count = parseInt(value);
    }
    toggleRangeContainer(value);
});

// Логика ползунка Минимум
$dom.minRange.on('input', () => {
    const minVal = parseInt($dom.minRange.value);

    $dom.maxRange.min = minVal;

    $dom.minTitle.textContent = `Минимум: ${minVal}`;
    saveMinEmotes(minVal);
});

// Логика ползунка Максимум
$dom.maxRange.on('input', () => {
    const maxVal = parseInt($dom.maxRange.value);

    $dom.minRange.max = maxVal;
    $dom.maxTitle.textContent = `Максимум: ${maxVal}`;
    saveMaxEmotes(maxVal);
});

function log(...args) {
    const div = document.getElementById("debug");

    div.textContent +=
        args.map(String).join(" ") + "\n";
}
const saveMinEmotes = $.debounce((val) => {
    $settings.min_emotes = val;
}, 0);

const saveMaxEmotes = $.debounce((val) => {
    $settings.max_emotes = val;
}, 0);