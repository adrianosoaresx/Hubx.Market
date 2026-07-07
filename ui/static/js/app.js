(function () {
    var storageKey = "hubx-color-theme";
    var root = document.documentElement;
    var media = window.matchMedia("(prefers-color-scheme: dark)");

    function readPreference() {
        try {
            return localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }

    function savePreference(preference) {
        try {
            localStorage.setItem(storageKey, preference);
        } catch (error) {
            return;
        }
    }

    function storedPreference() {
        var value = readPreference();
        return value === "light" || value === "dark" || value === "system" ? value : "system";
    }

    function resolvedTheme(preference) {
        if (preference === "light" || preference === "dark") {
            return preference;
        }
        return media.matches ? "dark" : "light";
    }

    function applyTheme(preference) {
        var theme = resolvedTheme(preference);
        root.dataset.colorTheme = theme;
        root.style.colorScheme = theme;

        document.querySelectorAll("[data-theme-option]").forEach(function (button) {
            var isActive = button.dataset.themeOption === preference;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(storedPreference());

        document.querySelectorAll("[data-theme-option]").forEach(function (button) {
            button.addEventListener("click", function () {
                var preference = button.dataset.themeOption;
                savePreference(preference);
                applyTheme(preference);

                var menu = button.closest("details");
                if (menu) {
                    menu.removeAttribute("open");
                }
            });
        });
    });

    media.addEventListener("change", function () {
        if (storedPreference() === "system") {
            applyTheme("system");
        }
    });
})();
