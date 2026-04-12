document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Initialize Icons (Lucide)
    lucide.createIcons();

    // 2. Matrix Background Canvas Logic
    const canvas = document.getElementById('matrix-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const letters = "0123456789ABCDEF!@#$%^&*()<>{}[]/-+".split('');
        const fontSize = 16;
        const columns = canvas.width / fontSize;
        const drops = Array(Math.floor(columns)).fill(1);
        
        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ff41';
            ctx.font = fontSize + 'px monospace';
            
            drops.forEach((y, i) => {
                const text = letters[Math.floor(Math.random() * letters.length)];
                ctx.fillText(text, i * fontSize, y * fontSize);
                if (y * fontSize > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            });
        }
        setInterval(drawMatrix, 40);

        // Handle window resize for canvas
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    }

    // 3. Dynamic Live Log Update
    const logEntries = [
        "> Core initialized. Welcome Michael & Guy.",
        "> Fetching M.Elizarov repositories... OK",
        "> Fetching G.Zwerdling repositories... OK",
        "> APT Intelligence Dashboard synced.",
        "> ziochub Threat Intel updated.",
        "> Network traffic secured."
    ];
    
    let currentLogIndex = 0;
    const logElement = document.getElementById("log-entry");
    
    if (logElement) {
        setInterval(() => {
            logElement.innerText = logEntries[currentLogIndex];
            currentLogIndex = (currentLogIndex + 1) % logEntries.length;
        }, 4000);
    }

    // 4. Interactive Terminal Typing Effect
    const terminal = document.getElementById('terminal');
    
    function typeTerminal(textList, index = 0) {
        if (!terminal) return;
        
        if (index < textList.length) {
            const cmdLine = document.createElement('div');
            cmdLine.className = 'cmd-line';
            
            // Allow HTML inside the terminal text for highlights
            cmdLine.innerHTML = `<span class="prompt">root@cybugs3:<span class="path">~</span># </span><span class="command">${textList[index]}</span>`;
            
            terminal.appendChild(cmdLine);
            terminal.scrollTop = terminal.scrollHeight;
            
            // Adjust speed: fast for normal lines, slower for empty lines (pauses)
            const speed = textList[index] === "" ? 400 : 800;
            setTimeout(() => typeTerminal(textList, index + 1), speed);
        }
    }

    // Start terminal sequence
    const startupText = [
        "CyBugs3 Framework [Version 3.1.2026]",
        "Authenticating developers...",
        "Identity verified: <span class='highlight'>Michael Elizarov</span> & <span class='highlight'>Guy Zwerdling</span>",
        "Loading Open Source Intelligence tools...",
        "Loading Splunk Detection Agents...",
        "System Operational. S³ Protocol Active.",
        "",
        "root@cybugs3:~$ ls -la /projects",
        "drwxr-xr-x 1 zwerd   staff  ziochub",
        "drwxr-xr-x 1 michael staff  apt-intelligence-dashboard",
        "drwxr-xr-x 1 michael staff  linkedin-osint-toolkit",
        "drwxr-xr-x 1 michael staff  splunk-detection-engineer-agent"
    ];
    
    setTimeout(() => {
        typeTerminal(startupText);
    }, 1000);
});
