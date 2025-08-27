document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const engineBtns = document.querySelectorAll('.engine-btn');
    const loadingDiv = document.getElementById('loading');
    const resultsArea = document.getElementById('results-area');
    const resultContent = document.getElementById('result-content');
    const resultSource = document.getElementById('result-source');
    const categoryButtonsDiv = document.getElementById('category-buttons');
    const saveConfirmationDiv = document.getElementById('save-confirmation');

    let selectedEngine = 'google';
    let currentSearchResult = {};

    // --- Event Listeners ---

    // Search engine selection
    engineBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            engineBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedEngine = btn.dataset.engine;
        });
    });

    // Search button click
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            handleSearch();
        }
    });

    // --- Functions ---

    async function handleSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            alert('検索キーワードを入力してください。');
            return;
        }

        // Reset UI
        resultsArea.classList.add('hidden');
        saveConfirmationDiv.classList.add('hidden');
        loadingDiv.classList.remove('hidden');

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, engine: selectedEngine }),
            });

            if (!response.ok) {
                throw new Error(`サーバーエラー: ${response.statusText}`);
            }

            const data = await response.json();
            currentSearchResult = { ...data, query };
            displayResults(data);

        } catch (error) {
            resultContent.textContent = `エラーが発生しました: ${error.message}`;
        } finally {
            loadingDiv.classList.add('hidden');
            resultsArea.classList.remove('hidden');
        }
    }

    function displayResults(data) {
        resultContent.textContent = data.content;
        resultSource.textContent = data.source_url;
        resultSource.href = data.source_url;

        categoryButtonsDiv.innerHTML = ''; // Clear old buttons
        data.suggestions.forEach(category => {
            const button = document.createElement('button');
            button.textContent = category;
            button.dataset.category = category;
            button.addEventListener('click', () => handleSave(category));
            categoryButtonsDiv.appendChild(button);
        });
    }

    async function handleSave(category) {
        // Highlight selected category button
        document.querySelectorAll('#category-buttons button').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.querySelector(`#category-buttons button[data-category="${category}"]`).classList.add('selected');

        const saveData = {
            title: currentSearchResult.query,
            content: currentSearchResult.content,
            url: currentSearchResult.source_url,
            query: currentSearchResult.query,
            category: category,
        };

        try {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saveData),
            });
            const result = await response.json();

            if (result.success) {
                showSaveConfirmation(true, `Notionに保存しました！ (Page ID: ${result.page_id})`);
            } else {
                throw new Error(result.error || '不明なエラー');
            }
        } catch (error) {
            showSaveConfirmation(false, `保存に失敗しました: ${error.message}`);
        }
    }

    function showSaveConfirmation(isSuccess, message) {
        saveConfirmationDiv.className = isSuccess ? 'success' : 'error';
        saveConfirmationDiv.textContent = message;
        saveConfirmationDiv.classList.remove('hidden');

        setTimeout(() => {
            saveConfirmationDiv.classList.add('hidden');
        }, 5000);
    }
});
