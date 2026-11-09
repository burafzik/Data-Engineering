import time
import json
import os
import sys
from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError, BadVersionError

ZK_HOSTS = "127.0.0.1:2181,127.0.0.1:2182,127.0.0.1:2183"
SESSION_TIMEOUT = 10
ELECTION_PATH = "/election/leader"
CHECKPOINT_PATH = "/calculation/checkpoint"
RESULT_PATH = "/calculation/result"
EPOCH_PATH = "/calculation/epoch"
TOTAL_CHUNKS = 10
CHUNK_DURATION = 5

class Coordinator:
    def __init__(self, coordinator_id):
        self.coordinator_id = coordinator_id
        self.zk = KazooClient(hosts=ZK_HOSTS, timeout=SESSION_TIMEOUT)
        self.is_leader = False
        self.current_epoch = 0
        self.fencing_enabled = False
        self.epoch_increased = False
        
    def start(self):
        self.zk.start()
        self.zk.ensure_path(ELECTION_PATH)
        self.zk.ensure_path("/calculation")
        if not self.zk.exists(CHECKPOINT_PATH):
            self.zk.create(CHECKPOINT_PATH, b'{"chunk": 0, "coordinator": ""}')
        if not self.zk.exists(EPOCH_PATH):
            self.zk.create(EPOCH_PATH, b"0")
        self.participate_in_election()
        
    def participate_in_election(self):
        election_node = self.zk.create(
            ELECTION_PATH + "/" + self.coordinator_id + "_",
            value=b"",
            ephemeral=True,
            sequence=True
        )
        children = self.zk.get_children(ELECTION_PATH)
        children.sort()
        if election_node.split("/")[-1] == children[0]:
            self.is_leader = True
            print(f"[{self.coordinator_id}] - лидер")
            if self.zk.exists(CHECKPOINT_PATH):
                checkpoint_data, _ = self.zk.get(CHECKPOINT_PATH)
                checkpoint = json.loads(checkpoint_data)
                last_chunk = checkpoint.get("chunk", 0)
                if last_chunk > 0:
                    print(f"[{self.coordinator_id}] Найден чекпоинт: чанк {last_chunk} обработан координатором {checkpoint.get('coordinator', 'unknown')}")
                    print(f"[{self.coordinator_id}] Возобновление расчёта с чанка {last_chunk}.")
                    self.calculate_from_checkpoint(last_chunk)
                else:
                    print(f"[{self.coordinator_id}] Начало расчёта с чанка 0")
                    self.calculate_from_checkpoint(0)
            else:
                print(f"[{self.coordinator_id}] Начало расчёта с чанка 0")
                self.calculate_from_checkpoint(0)
        else:
            print(f"[{self.coordinator_id}] - запасной")
            self.watch_for_leader_failure()
            
    def watch_for_leader_failure(self):
        print(f"[{self.coordinator_id}] Ожидание отказа лидера")
        @self.zk.ChildrenWatch(ELECTION_PATH)
        def watch_children(children):
            children.sort()
            if len(children) > 0 and children[0].startswith(self.coordinator_id + "_"):
                print(f"[{self.coordinator_id}] - новый лидер")
                self.is_leader = True
                if self.zk.exists(CHECKPOINT_PATH):
                    checkpoint_data, _ = self.zk.get(CHECKPOINT_PATH)
                    checkpoint = json.loads(checkpoint_data)
                    last_chunk = checkpoint.get("chunk", 0)
                    print(f"[{self.coordinator_id}] Найден чекпоинт: чанк {last_chunk} обработан координатором {checkpoint.get('coordinator', 'unknown')}")
                    print(f"[{self.coordinator_id}] Возобновление расчёта с чанка {last_chunk}")
                    self.calculate_from_checkpoint(last_chunk)
                else:
                    print(f"[{self.coordinator_id}] Чекпоинт не найден, начинаем с 0")
                    self.calculate_from_checkpoint(0)
                    
    def run_calculation(self):
        self.calculate_from_checkpoint(0)
        
    def resume_calculation(self):
        if self.zk.exists(CHECKPOINT_PATH):
            checkpoint_data, _ = self.zk.get(CHECKPOINT_PATH)
            checkpoint = json.loads(checkpoint_data)
            last_chunk = checkpoint["chunk"]
            print(f"[{self.coordinator_id}] Найден чекпоинт: чанк {last_chunk} обработан координатором {checkpoint.get('coordinator', 'unknown')}")
            print(f"[{self.coordinator_id}] Возобновление расчёта с чанка {last_chunk}/")
            self.calculate_from_checkpoint(last_chunk)
        else:
            print(f"[{self.coordinator_id}] Чекпоинт не найден, начинаем с 0")
            self.calculate_from_checkpoint(0)
            
    def calculate_from_checkpoint(self, start_chunk):
        if self.fencing_enabled and not self.epoch_increased:
            self.increment_epoch()
            self.epoch_increased = True
        if not self.zk.exists(CHECKPOINT_PATH):
            self.zk.create(CHECKPOINT_PATH, json.dumps({"chunk": 0, "coordinator": self.coordinator_id}).encode())
        for chunk_id in range(start_chunk, TOTAL_CHUNKS):
            if not self.is_leader:
                print(f"[{self.coordinator_id}] Потерял лидерство, останавливаю расчёт")
                return
            print(f"[{self.coordinator_id}] Обработка чанка {chunk_id}/{TOTAL_CHUNKS}")
            time.sleep(CHUNK_DURATION)
            checkpoint = {"chunk": chunk_id + 1, "coordinator": self.coordinator_id}
            self.zk.set(CHECKPOINT_PATH, json.dumps(checkpoint).encode())
            print(f"[{self.coordinator_id}] Чекпоинт сохранён: чанк {chunk_id + 1} обработан")
        self.write_result()
        
    def increment_epoch(self):
        if not self.zk.exists(EPOCH_PATH):
            self.zk.create(EPOCH_PATH, b"0")
        epoch_data, stat = self.zk.get(EPOCH_PATH)
        current_epoch = int(epoch_data)
        self.current_epoch = current_epoch + 1
        self.zk.set(EPOCH_PATH, str(self.current_epoch).encode())
        print(f"[{self.coordinator_id}] Эпоха увеличена до {self.current_epoch}")
        
    def write_result(self):
        result = {
            "coordinator": self.coordinator_id,
            "epoch": self.current_epoch,
            "total_chunks": TOTAL_CHUNKS,
            "timestamp": time.time()
        }
        
        result_data = json.dumps(result).encode()
        
        if self.fencing_enabled:
            try:
                if not self.zk.exists(RESULT_PATH):
                    self.zk.create(RESULT_PATH, result_data)
                    print(f"[{self.coordinator_id}] Результат записан (эпоха {self.current_epoch})")
                else:
                    print(f"[{self.coordinator_id}] Отклонено: результат уже записан координатором {json.loads(self.zk.get(RESULT_PATH)[0]).get('coordinator')} с эпохой {json.loads(self.zk.get(RESULT_PATH)[0]).get('epoch')}")
            except BadVersionError:
                print(f"[{self.coordinator_id}] BadVersionError: результат уже записан другим координатором")
        else:
            if not self.zk.exists(RESULT_PATH):
                self.zk.create(RESULT_PATH, result_data)
            else:
                self.zk.set(RESULT_PATH, result_data)
            print(f"[{self.coordinator_id}] Результат записан (версия узла: {self.zk.get(RESULT_PATH)[1].version})")
            
    def stop(self):
        print(f"[{self.coordinator_id}] Остановка координатора")
        self.zk.stop()
        self.zk.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python coordinator.py <coordinator_id>")
        sys.exit(1)
    coordinator_id = sys.argv[1]
    fencing = os.environ.get("FENCING", "0") == "1"
    coord = Coordinator(coordinator_id)
    coord.fencing_enabled = fencing
    if fencing:
        print(f"[{coordinator_id}] Режим: с защитой (FENCING=1)")
    else:
        print(f"[{coordinator_id}] Режим: без защиты (FENCING=0)")
    try:
        coord.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{coordinator_id}] Получен сигнал остановки, закрываем сессию")
        coord.stop()
        print(f"[{coordinator_id}] Сессия закрыта, эфемерные узлы удалены")