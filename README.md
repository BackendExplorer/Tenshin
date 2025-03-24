sequenceDiagram
    autonumber

    participant ユーザー
    participant ブラウザ
    participant フロントエンド
    participant バックエンド
    participant PokémonAPI

    ユーザー->>ブラウザ: アプリのURLにアクセス
    ブラウザ->>フロントエンド: 初期画面のロード
    note right of フロントエンド: Reactアプリが起動

    フロントエンド->>バックエンド: ポケモン一覧取得リクエスト (GET /pokemons)
    バックエンド->>PokémonAPI: ポケモン一覧データを取得 (https://pokeapi.co/api/v2/pokemon?...)
    PokémonAPI-->>バックエンド: ポケモン一覧データ (JSON)
    バックエンド-->>フロントエンド: ポケモン一覧データ (JSON)

    note over フロントエンド: Reactで一覧を表示

    ユーザー->>フロントエンド: 一覧からポケモンをクリック
    フロントエンド->>バックエンド: 特定のポケモン詳細リクエスト (GET /pokemons/:id)
    バックエンド->>PokémonAPI: ポケモン詳細データを取得 (https://pokeapi.co/api/v2/pokemon/{id})
    PokémonAPI-->>バックエンド: ポケモン詳細データ (JSON)
    バックエンド-->>フロントエンド: ポケモン詳細データ (JSON)

    note over フロントエンド: Reactで詳細画面を表示
